"""Independently validate the fitted-path temporal-authority successor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.data.cycle26_bound_authority_pair_audit import (  # noqa: E402
    CONSERVATIVE_BOUND,
    OBSERVED_EFFECTIVE,
    OBSERVED_PUBLICATION,
    operational_pit_admission_allowed,
)

AUTHORITY_GATE = "artifacts/data_lake/historical_known_at_authority_gate.json"
SUITE_GATE = "artifacts/forecast/week1_2026_national_forecast_suite_gate.json"
WEEK1_GATE = (
    "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
)
SUCCESSOR_GATE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_FITTED_PATH_TEMPORAL_AUTHORITY.json"
)


def _load(repo: Path, relative: str) -> dict:
    return json.loads((repo / relative).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO))
    args = parser.parse_args()
    repo = Path(args.repo_root)
    findings: list[str] = []
    authority = _load(repo, AUTHORITY_GATE)
    suite = _load(repo, SUITE_GATE)
    week1 = _load(repo, WEEK1_GATE)
    successor = _load(repo, SUCCESSOR_GATE)
    counts = authority.get("authority_class_counts") or {}
    observed_publication = int(counts.get(OBSERVED_PUBLICATION) or 0)
    observed_effective = int(counts.get(OBSERVED_EFFECTIVE) or 0)
    training_row_count = int(
        (suite.get("deployment_fit") or {}).get("training_row_count") or 0
    )
    trust = week1.get("trust") or {}
    assessment = successor.get("assessment") or {}
    if operational_pit_admission_allowed(
        CONSERVATIVE_BOUND, predecessor_sufficient=True
    ):
        findings.append("CONSERVATIVE_BOUND_TREATED_AS_PROVEN_PIT")
    if observed_publication != 0 or observed_effective != 0:
        findings.append("UNEXPECTED_PROVEN_PIT_DOMAIN_COUNT")
    if assessment.get("proven_pit_training_row_count") not in (0, None):
        findings.append("PROVEN_PIT_TRAINING_ROWS_CLAIMED_WITHOUT_AUTHORITY")
    if assessment.get("training_row_count") != training_row_count:
        findings.append("TRAINING_ROW_COUNT_MISMATCH")
    if assessment.get("refit_without_proxy_pairs_possible") is True:
        findings.append("FALSE_REFIT_WITHOUT_PROXY_CLAIM")
    if assessment.get("week1_payloads_rewritten") is True:
        findings.append("WEEK1_PAYLOAD_REWRITE_CLAIMED")
    if assessment.get("primary_trust_recovery") != "PRIMARY_TRUST_RECOVERY_INCOMPLETE":
        findings.append("PRIMARY_TRUST_RECOVERY_MISLABELED")
    if trust.get("ACTIVE_PATH_CORRECTNESS_CLAIM") is True:
        findings.append("WEEK1_ACTIVE_PATH_CORRECTNESS_CLAIM_TRUE")
    if trust.get("publication_label") != "UNTRUSTED_SHADOW":
        findings.append("WEEK1_PUBLICATION_NOT_UNTRUSTED_SHADOW")
    if successor.get("result") != "PASS_FITTED_PATH_TEMPORAL_AUTHORITY_CONTAINED":
        findings.append("SUCCESSOR_RESULT_NOT_CONTAINED")
    payload = {
        "validator": "week1_2026_fitted_path_temporal_authority",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "gate_identity": successor.get("gate_identity"),
        "observed_publication_domains": observed_publication,
        "observed_effective_domains": observed_effective,
        "training_row_count": training_row_count,
        "proven_pit_training_row_count": assessment.get(
            "proven_pit_training_row_count"
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())

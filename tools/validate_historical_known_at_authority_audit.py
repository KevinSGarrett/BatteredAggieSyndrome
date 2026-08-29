"""Independently validate the historical known-at authority audit gate.

The validator is read-only and offline. It re-derives the start-time evidence profile from
the national spine when a data root is mounted, and it refuses any gate that promotes a
retrieval timestamp or an unlabeled assumption into a historical known-at claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.historical_known_at_authority import (  # noqa: E402
    CONSERVATIVE_BOUND,
    GATE_RELATIVE,
    KnownAtAuthorityViolation,
    profile_start_evidence,
    read_json,
    validate_artifact,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_historical_known_at_authority_audit import load_spine_rows  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    summary = validate_artifact(repo_root)
    gate = read_json(repo_root / GATE_RELATIVE)

    checks: list[dict[str, object]] = []

    bounded = [
        row["domain_id"]
        for row in gate["domain_authority"]
        if row["authority_class"] == CONSERVATIVE_BOUND
    ]
    label = gate["conservative_bound_policy"].get("label", "")
    if bounded and "BOUND_NOT_AN_OBSERVED" not in label:
        raise KnownAtAuthorityViolation("a bounded domain is not labeled as a bound")
    checks.append({"bounded_domains": bounded, "check": "BOUND_IS_LABELED_AS_A_BOUND", "state": "PASS"})

    if not gate["negative_findings"][
        "no_capture_or_retrieval_time_was_used_as_a_historical_known_at_instant"
    ]:
        raise KnownAtAuthorityViolation("the gate admits using a retrieval time as a known-at instant")
    checks.append({"check": "NO_RETRIEVAL_TIME_USED_AS_KNOWN_AT", "state": "PASS"})

    if gate["gap_verdict"]["remains_open"] is False and gate[
        "domains_blocked_from_point_in_time_admission"
    ]:
        raise KnownAtAuthorityViolation("GAP-002 is closed while domains remain blocked")
    checks.append({"check": "GAP_002_NOT_FALSELY_CLOSED", "state": "PASS"})

    data_root = args.data_root.resolve() if args.data_root else None
    if data_root is not None and data_root.exists():
        rederived = profile_start_evidence(load_spine_rows(repo_root, data_root))
        if rederived != gate["start_time_evidence_profile"]:
            raise KnownAtAuthorityViolation(
                "the committed start-time evidence profile does not reproduce from the spine"
            )
        checks.append({"check": "START_TIME_PROFILE_REPRODUCES_FROM_SPINE", "state": "PASS"})
    else:
        checks.append(
            {"check": "START_TIME_PROFILE_REPRODUCES_FROM_SPINE", "state": "SKIP_DATA_ROOT_ABSENT"}
        )

    print(json.dumps({**summary, "checks": checks}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

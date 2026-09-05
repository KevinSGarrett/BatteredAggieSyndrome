"""Independently validate the remaining all-cycle claim census."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE = "artifacts/scientific_integrity/cycle26/CYCLE26_REMAINING_CLAIM_CENSUS.json"
ALLOWED = {
    "NOT_AUDITED_YET",
    "RECONSTRUCTED_NAMED_CHECK_NOT_WHOLE_CYCLE",
    "FAIL",
}
MINIMUM_CLAIM_COUNT = 31


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO))
    args = parser.parse_args()
    gate = json.loads((Path(args.repo_root) / GATE).read_text(encoding="utf-8"))
    findings: list[str] = []
    claims = gate.get("claims") or []
    if not claims:
        findings.append("CLAIM_REGISTRY_EMPTY")
    if len(claims) < MINIMUM_CLAIM_COUNT:
        findings.append("CLAIM_CENSUS_BELOW_MINIMUM")
    seen: set[str] = set()
    counts = {
        "NOT_AUDITED_YET": 0,
        "RECONSTRUCTED_NAMED_CHECK_NOT_WHOLE_CYCLE": 0,
        "FAIL": 0,
    }
    for row in claims:
        claim_id = str(row.get("claim_id") or "")
        if not claim_id:
            findings.append("CLAIM_ID_MISSING")
            continue
        if claim_id in seen:
            findings.append(f"DUPLICATE_CLAIM_ID:{claim_id}")
        seen.add(claim_id)
        status = str(row.get("status") or "")
        if status not in ALLOWED:
            findings.append(f"ILLEGAL_CLAIM_CLASS:{claim_id}:{status}")
        elif status in counts:
            counts[status] += 1
        if not row.get("remaining"):
            findings.append(f"EMPTY_REMAINING:{claim_id}")
        if (
            status == "RECONSTRUCTED_NAMED_CHECK_NOT_WHOLE_CYCLE"
            and claim_id.startswith("C")
            and not claim_id.startswith("NAMED-")
        ):
            findings.append(f"NAMED_CHECK_USED_WHOLE_CYCLE_ID:{claim_id}")
    if gate.get("semantically_audited") is True:
        findings.append("SEMANTICALLY_AUDITED_FALSE_STAMP")
    if gate.get("ALL_CYCLE_SCIENTIFIC_TRUST_GATE") is True:
        findings.append("TRUST_GATE_MUST_NOT_CLAIM_RECOVERY_WHILE_HOLD_ACTIVE")
    if counts["NOT_AUDITED_YET"] < 1:
        findings.append("UNREVIEWED_REMAINING_CLAIMS_HIDDEN")
    if gate.get("unreviewed_remaining_claim_count") != counts["NOT_AUDITED_YET"]:
        findings.append("UNREVIEWED_COUNT_MISMATCH")
    payload = {
        "validator": "cycle26_remaining_claim_census",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "claim_count": len(claims),
        "status_counts": counts,
        "gate_identity": gate.get("gate_identity"),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())

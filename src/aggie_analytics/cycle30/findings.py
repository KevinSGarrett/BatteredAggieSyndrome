"""Cycle #30 finding successor ledger.

Preserves Cycle #28 P0 identifiers and maps Cycle #29 manager findings.
"""

from __future__ import annotations

from typing import Any

CONFIRMED_FIXED = "CONFIRMED_FIXED"
FALSE_POSITIVE_PROVEN = "FALSE_POSITIVE_PROVEN"
DUPLICATE = "DUPLICATE"
BLOCKED_WITH_CONTAINMENT = "BLOCKED_WITH_CONTAINMENT"
ACCEPTED_RISK_USER_APPROVED = "ACCEPTED_RISK_USER_APPROVED"
REGRESSION_RETEST = "REGRESSION_RETEST_REQUIRED"

ALLOWED = {
    CONFIRMED_FIXED,
    FALSE_POSITIVE_PROVEN,
    DUPLICATE,
    BLOCKED_WITH_CONTAINMENT,
    ACCEPTED_RISK_USER_APPROVED,
}

C28_P0_IDS = tuple(f"C28-P0-{index:02d}" for index in range(1, 13))
C29_FINDING_IDS = (
    "S29-01",
    "S29-02",
    "S29-03",
    "S29-04",
    "S29-05",
    "S29-06",
    "S29-07",
    "S29-08",
    "N29-01",
    "N29-02",
    "N29-03",
    "I29-01",
    "I29-02",
    "I29-03",
    "I29-04",
    "I29-05",
    "I29-06",
    "A29-01",
    "A29-02",
    "A29-03",
)


class FindingError(ValueError):
    """Raised when a finding disposition is invalid."""


def require_disposition(finding_id: str, disposition: str) -> str:
    if disposition not in ALLOWED:
        raise FindingError(f"{finding_id} has invalid disposition {disposition}")
    if disposition in {FALSE_POSITIVE_PROVEN, ACCEPTED_RISK_USER_APPROVED}:
        raise FindingError(
            f"{finding_id}: Cursor may propose but not solely authorize {disposition}"
        )
    return disposition


def successor_ledger() -> dict[str, Any]:
    rows = [
        _row(
            "C28-P0-01",
            CONFIRMED_FIXED,
            "claim completeness fails closed on unmapped exact pointers",
            "tests/test_cycle30_adversarial_controls.py",
        ),
        _row(
            "C28-P0-02",
            CONFIRMED_FIXED,
            "cycle30 producer and reference trees are disjoint",
            "tests/test_cycle30_adversarial_controls.py",
        ),
        _row(
            "C28-P0-03",
            CONFIRMED_FIXED,
            "official finals require canonical participant IDs",
            "src/aggie_analytics/cycle30/scoring.py",
        ),
        _row(
            "C28-P0-04",
            CONFIRMED_FIXED,
            "timestamps parse as aware UTC instants; midnight is not date-only",
            "src/aggie_analytics/cycle30/temporal.py",
        ),
        _row(
            "C28-P0-05",
            CONFIRMED_FIXED,
            "probability/interval coherence independently reconstructed",
            "src/aggie_analytics/scientific_reference/cycle30/metrics.py",
        ),
        _row(
            "C28-P0-06",
            CONFIRMED_FIXED,
            "forecast immutability reconstructed from row bytes",
            "src/aggie_analytics/cycle30/forecast.py",
        ),
        _row(
            "C28-P0-07",
            BLOCKED_WITH_CONTAINMENT,
            "atomic checkpoint lease retained; no new jobs created this cycle",
            "src/aggie_analytics/cycle30/lease.py",
        ),
        _row(
            "C28-P0-08",
            CONFIRMED_FIXED,
            "CI opens/rehashes fixture rows or fail-closed blocked",
            "src/aggie_analytics/cycle30/ci_rows.py",
        ),
        _row(
            "C28-P0-09",
            BLOCKED_WITH_CONTAINMENT,
            "eligible/oriented/proven identities reconciled; proven PIT may remain zero",
            "src/aggie_analytics/cycle30/pit_kernel.py",
        ),
        _row(
            "C28-P0-10",
            BLOCKED_WITH_CONTAINMENT,
            "All-22 C01 release/BOM not consumed until immutable",
            "src/aggie_analytics/cycle30/gridiron.py",
        ),
        _row(
            "C28-P0-11",
            BLOCKED_WITH_CONTAINMENT,
            "national coverage census exists; completeness not claimed",
            "src/aggie_analytics/cycle30/populations.py",
        ),
        _row(
            "C28-P0-12",
            CONFIRMED_FIXED,
            "pair counts derived home→away from rows; FCS-v-FCS remains observed numerator",
            "src/aggie_analytics/cycle30/populations.py",
        ),
        _row(
            "S29-01",
            BLOCKED_WITH_CONTAINMENT,
            "synthetic placeholders quarantined; real membership/coaching attempts required",
            "tools/materialize_cycle30.py",
        ),
        _row(
            "S29-02",
            CONFIRMED_FIXED,
            "claim discovery uses artifact+pointer+row+field; undeclared files fail",
            "src/aggie_analytics/cycle30/claims.py",
        ),
        _row(
            "S29-03",
            CONFIRMED_FIXED,
            "science vs containment split; empty files cannot PASS science",
            "tools/validate_cycle30_gates.py",
        ),
        _row(
            "S29-04",
            CONFIRMED_FIXED,
            "independent score/tie/authority specification; global flags not proof",
            "src/aggie_analytics/cycle30/pit_kernel.py",
        ),
        _row(
            "S29-05",
            CONFIRMED_FIXED,
            "home→away pair counts derived from rows",
            "src/aggie_analytics/cycle30/populations.py",
        ),
        _row(
            "S29-06",
            CONFIRMED_FIXED,
            "contest-scoped terminal status; neighborhood Final is not terminal",
            "src/aggie_analytics/cycle30/acquisition.py",
        ),
        _row(
            "S29-07",
            CONFIRMED_FIXED,
            "row-bound person/title extraction; equal-length arrays rejected",
            "src/aggie_analytics/cycle30/coaching.py",
        ),
        _row(
            "S29-08",
            CONFIRMED_FIXED,
            "one-to-many requirement mappings preserve distinct current domains",
            "src/aggie_analytics/cycle30/domains.py",
        ),
        _row(
            "N29-01",
            CONFIRMED_FIXED,
            "ordinary_home_exposure zero at verified neutrals for every fitted path",
            "src/aggie_analytics/cycle30/site_context.py",
        ),
        _row(
            "N29-02",
            CONFIRMED_FIXED,
            "missing neutral annotation is UNKNOWN not ordinary home",
            "src/aggie_analytics/cycle30/site_context.py",
        ),
        _row(
            "N29-03",
            BLOCKED_WITH_CONTAINMENT,
            "travel rows exist; consumed-column proof required per candidate",
            "src/aggie_analytics/cycle30/site_context.py",
        ),
        _row(
            "I29-01",
            BLOCKED_WITH_CONTAINMENT,
            "PR review threads independently adjudicated; not auto-fixed by outdated",
            "artifacts/scientific_integrity/cycle30",
        ),
        _row(
            "I29-02",
            CONFIRMED_FIXED,
            "no-API attestation separated from scientific review gate",
            "src/aggie_analytics/cycle30/cost.py",
        ),
        _row(
            "I29-03",
            BLOCKED_WITH_CONTAINMENT,
            "Codecov patch coverage reported as informational; thresholds not restored",
            "src/aggie_analytics/cycle30/cost.py",
        ),
        _row(
            "I29-04",
            BLOCKED_WITH_CONTAINMENT,
            "GameContextV2 proposal delivered; C01 adoption pending owner",
            "docs/contracts/proposed",
        ),
        _row(
            "I29-05",
            BLOCKED_WITH_CONTAINMENT,
            "StaffSnapshotV2/CoachStateV2 proposal delivered; adoption pending",
            "docs/contracts/proposed",
        ),
        _row(
            "I29-06",
            BLOCKED_WITH_CONTAINMENT,
            "integration inventory is exact counts not four-field booleans",
            "src/aggie_analytics/cycle30/gridiron.py",
        ),
        _row(
            "A29-01",
            CONFIRMED_FIXED,
            "future publication rejected; conservative bounds labeled not proven",
            "src/aggie_analytics/cycle30/pit_kernel.py",
        ),
        _row(
            "A29-02",
            CONFIRMED_FIXED,
            "future-append rebuilds kernel; keyed semantics compared",
            "src/aggie_analytics/cycle30/pit_kernel.py",
        ),
        _row(
            "A29-03",
            CONFIRMED_FIXED,
            "exact midnight UTC is not inferred date-only precision",
            "src/aggie_analytics/cycle30/temporal.py",
        ),
    ]
    missing_p0 = [
        item for item in C28_P0_IDS if item not in {row["finding_id"] for row in rows}
    ]
    if missing_p0:
        raise FindingError(f"manager-audit P0 identifiers omitted: {missing_p0}")
    missing_c29 = [
        item
        for item in C29_FINDING_IDS
        if item not in {row["finding_id"] for row in rows}
    ]
    if missing_c29:
        raise FindingError(f"Cycle29 findings omitted: {missing_c29}")
    return {
        "artifact_type": "CYCLE30_FINDING_SUCCESSOR_LEDGER",
        "operator_hold": "ACTIVE",
        "cursor_cannot_authorize_false_positive_or_accepted_risk": True,
        "rows": rows,
        "p0_count": 12,
        "p0_ids_preserved": list(C28_P0_IDS),
        "c29_finding_ids": list(C29_FINDING_IDS),
        "review_state": "READY_FOR_MANAGER_REVIEW",
    }


def _row(
    finding_id: str, disposition: str, evidence: str, retest: str
) -> dict[str, str]:
    return {
        "finding_id": finding_id,
        "disposition": require_disposition(finding_id, disposition),
        "evidence": evidence,
        "retest": retest,
        "regression_test_required": "true"
        if disposition == CONFIRMED_FIXED
        else "false",
    }

"""Cycle #28 finding successor ledger.

Preserves manager-audit identifiers exactly.
"""

from __future__ import annotations

from typing import Any

CONFIRMED_FIXED = "CONFIRMED_FIXED"
FALSE_POSITIVE_PROVEN = "FALSE_POSITIVE_PROVEN"
DUPLICATE = "DUPLICATE"
BLOCKED_WITH_CONTAINMENT = "BLOCKED_WITH_CONTAINMENT"
ACCEPTED_RISK_USER_APPROVED = "ACCEPTED_RISK_USER_APPROVED"

ALLOWED = {
    CONFIRMED_FIXED,
    FALSE_POSITIVE_PROVEN,
    DUPLICATE,
    BLOCKED_WITH_CONTAINMENT,
    ACCEPTED_RISK_USER_APPROVED,
}

C28_P0_IDS = tuple(f"C28-P0-{index:02d}" for index in range(1, 13))


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
            "claim completeness now fails closed on unmapped claims",
        ),
        _row(
            "C28-P0-02",
            CONFIRMED_FIXED,
            "cycle29 producer and reference trees are disjoint",
        ),
        _row(
            "C28-P0-03",
            CONFIRMED_FIXED,
            "official finals require canonical participant IDs",
        ),
        _row("C28-P0-04", CONFIRMED_FIXED, "timestamps parse as aware UTC instants"),
        _row(
            "C28-P0-05",
            CONFIRMED_FIXED,
            "probability/interval coherence independently reconstructed",
        ),
        _row(
            "C28-P0-06",
            CONFIRMED_FIXED,
            "forecast immutability reconstructed from row bytes",
        ),
        _row(
            "C28-P0-07",
            CONFIRMED_FIXED,
            "atomic checkpoint lease; duplicate SMU writer stopped",
        ),
        _row(
            "C28-P0-08",
            CONFIRMED_FIXED,
            "CI opens/rehashes fixture rows or fail-closed blocked",
        ),
        _row(
            "C28-P0-09",
            BLOCKED_WITH_CONTAINMENT,
            "89855/90198/zero contradiction bound; kernel may be nonzero but expected-FBS population remains blocked",
        ),
        _row(
            "C28-P0-10",
            BLOCKED_WITH_CONTAINMENT,
            "All-22 C01 release/BOM not consumed until immutable",
        ),
        _row(
            "C28-P0-11",
            BLOCKED_WITH_CONTAINMENT,
            "national coverage census exists; completeness not claimed",
        ),
        _row(
            "C28-P0-12",
            BLOCKED_WITH_CONTAINMENT,
            "46953-game payload classified FBS_CENTRIC; FCS-v-FCS expected universe independently gated",
        ),
        _row("C28-P0-11a", CONFIRMED_FIXED, "empty/empty inventories cannot PASS"),
        _row(
            "C28-P0-11b", CONFIRMED_FIXED, "zero-filled capability registry superseded"
        ),
        _row("C28-P0-11c", CONFIRMED_FIXED, "display names are not canonical IDs"),
        _row(
            "C28-P1-BASE-RATE-0.5",
            CONFIRMED_FIXED,
            "0.5 excluded from directional accuracy",
        ),
        _row(
            "C28-P1-REQUEST-IDENTITY",
            CONFIRMED_FIXED,
            "request identity excludes PID/time",
        ),
        _row(
            "C28-P1-RECEIPT-FALLBACK",
            CONFIRMED_FIXED,
            "arbitrary last-receipt fallback removed",
        ),
        _row(
            "C28-P1-CHECKPOINT-WINDOW",
            CONFIRMED_FIXED,
            "checkpoint window from calendar authority",
        ),
        _row(
            "C28-P1-WEEK1-UNRESOLVED-FIELD",
            CONFIRMED_FIXED,
            "predecessor 8 vs successor 0 split",
        ),
        _row(
            "C28-P1-STAFF-2382",
            BLOCKED_WITH_CONTAINMENT,
            "provisional staff observations reconciled, not admitted",
        ),
        _row(
            "C28-P1-ERA-LABELS",
            CONFIRMED_FIXED,
            "modern FBS/FCS not projected pre-1978",
        ),
        _row(
            "C28-P1-MISSOURI-STATE",
            BLOCKED_WITH_CONTAINMENT,
            "52-game prior incomplete FCS graph",
        ),
        _row(
            "C28-P1-PAID-REVIEW",
            CONFIRMED_FIXED,
            "metered API restricted to explicit authorization",
        ),
        _row(
            "C28-P1-ABSOLUTE-PATHS",
            CONFIRMED_FIXED,
            "public artifacts use relative/portable paths",
        ),
        _row(
            "C28-P1-DIFF-CHECK",
            BLOCKED_WITH_CONTAINMENT,
            "line endings diagnosed, not mass-normalized",
        ),
    ]
    missing = [
        item for item in C28_P0_IDS if item not in {row["finding_id"] for row in rows}
    ]
    if missing:
        raise FindingError(f"manager-audit P0 identifiers omitted: {missing}")
    return {
        "artifact_type": "CYCLE29_FINDING_SUCCESSOR_LEDGER",
        "operator_hold": "ACTIVE",
        "cursor_cannot_authorize_false_positive_or_accepted_risk": True,
        "rows": rows,
        "p0_count": 12,
        "p0_ids_preserved": list(C28_P0_IDS),
    }


def _row(finding_id: str, disposition: str, evidence: str) -> dict[str, str]:
    return {
        "finding_id": finding_id,
        "disposition": require_disposition(finding_id, disposition),
        "evidence": evidence,
        "regression_test_required": "true"
        if disposition == CONFIRMED_FIXED
        else "false",
    }

"""Standing Cycle32 completion-contract states. Not scientific acceptance."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

ALLOWED_CYCLE_STATES = (
    "NOT_STARTED",
    "IN_PROGRESS",
    "IMPLEMENTED_PENDING_VERIFICATION",
    "VERIFIED",
    "BLOCKED_EXTERNAL",
    "PENDING_MANAGER_REVIEW",
    "PENDING_RELEASE_AUTHORITY",
    "NOT_APPLICABLE",
    "DEFERRED_USER_APPROVED",
)
SUCCESS_STATES = frozenset({"VERIFIED"})
HOLD_PROTECTED_STATES = frozenset({"PENDING_RELEASE_AUTHORITY"})
FORBIDDEN_HEADLINES = frozenset(
    {
        "CYCLE_COMPLETE",
        "COMPLETE_UNDER_HOLD",
        "ALL_LOCAL_RECONSTRUCTION_COMPLETE",
    }
)


class CycleCompletionError(ValueError):
    """Raised when a ledger or report contradicts the completion contract."""


def validate_state(state: str) -> str:
    token = str(state or "").strip()
    if token not in ALLOWED_CYCLE_STATES:
        raise CycleCompletionError(f"invalid cycle state {token!r}")
    return token


def cannot_mark_external_blocked_while_local_counterexample_fails(
    *, locally_failing: bool, state: str
) -> None:
    if locally_failing and state == "BLOCKED_EXTERNAL":
        raise CycleCompletionError(
            "a locally failing function cannot be marked only BLOCKED_EXTERNAL"
        )


def cannot_map_placeholder_as_complete(*, resolved: bool, placeholder: bool) -> None:
    if placeholder and resolved:
        raise CycleCompletionError("generic placeholder cannot be mapped 100%")


def require_source_head_match(*, reported_head: str, actual_head: str) -> None:
    if str(reported_head or "") != str(actual_head or ""):
        raise CycleCompletionError("source-HEAD mismatch")


def require_requirement_present(
    requirement_ids: Sequence[str], *, expected: Sequence[str]
) -> None:
    missing = [rid for rid in expected if rid not in set(requirement_ids)]
    if missing:
        raise CycleCompletionError(f"missing requirement {missing}")


def cannot_pass_with_skipped_required_test(*, skipped_required: bool, result: str) -> None:
    if skipped_required and str(result).upper() == "PASS":
        raise CycleCompletionError("skipped required test cannot produce PASS")


def unique_test_coverage(*, executions: int, unique_tests: int) -> int:
    if executions < unique_tests:
        raise CycleCompletionError("coverage count exceeds unique tests")
    if unique_tests < 0 or executions < 0:
        raise CycleCompletionError("test counts must be non-negative")
    return unique_tests


def validate_ledger(payload: Mapping[str, Any]) -> dict[str, Any]:
    headline = str(payload.get("headline") or "")
    if headline in FORBIDDEN_HEADLINES:
        raise CycleCompletionError(f"forbidden headline {headline}")
    hold = str(payload.get("hold") or "")
    if headline == "CYCLE_COMPLETE":
        raise CycleCompletionError("CYCLE_COMPLETE is not authorized")
    if hold == "ACTIVE" and "COMPLETE" in headline and "NOT_ACCEPTED" not in headline:
        raise CycleCompletionError("cannot say complete under hold")
    rows = list(payload.get("requirements") or [])
    if not rows:
        raise CycleCompletionError("missing requirement")
    ids = [str(row.get("requirement_id") or "") for row in rows]
    require_requirement_present(ids, expected=payload.get("expected_ids") or [])
    for row in rows:
        state = validate_state(str(row.get("state") or ""))
        if row.get("locally_failing_counterexample") and state in {
            "BLOCKED_EXTERNAL",
            "PENDING_MANAGER_REVIEW",
            "VERIFIED",
        }:
            raise CycleCompletionError(
                f"{row.get('requirement_id')} still fails a known counterexample"
            )
        if row.get("placeholder_mapped_complete"):
            raise CycleCompletionError("generic placeholder cannot be mapped 100%")
        if not row.get("owner_keys") and not row.get("owner"):
            raise CycleCompletionError(f"{row.get('requirement_id')} missing owner")
    reported = str(payload.get("git_head") or "")
    actual = str(payload.get("actual_git_head") or reported)
    require_source_head_match(reported_head=reported, actual_head=actual)
    return {
        "headline": headline,
        "requirement_count": len(rows),
        "hold": hold,
        "valid": True,
    }

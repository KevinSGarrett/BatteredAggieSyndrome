"""Review-cost containment. No-API attestation is not scientific review approval."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


class CostError(ValueError):
    """Raised when paid review control is violated."""


def reject_routine_api_review(
    event: str, authorized_tuple: dict[str, Any] | None
) -> None:
    if event == "pull_request" and authorized_tuple is None:
        raise CostError("routine API review firing without exact user authorization")
    if authorized_tuple is not None:
        required = ("pr", "head", "model", "effort", "max_spend_usd")
        missing = [field for field in required if not authorized_tuple.get(field)]
        if missing:
            raise CostError(f"paid review authorization missing {missing}")


def attestation_check(
    *,
    head_sha: str,
    review_identities: list[str],
    api_calls: int,
    scientific_reviews: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    scientific = list(scientific_reviews or [])
    scientific_state = "PENDING_BLOCKED"
    if scientific:
        current = [
            row
            for row in scientific
            if str(row.get("head_sha")) == head_sha
            and row.get("complete_pagination")
            and row.get("persistent_artifact")
            and row.get("reviewer_identity")
        ]
        scientific_state = "PRESENT" if current else "STALE_OR_INCOMPLETE"
    return {
        "artifact_type": "CYCLE30_CODEX_CLOUD_REVIEW_ATTESTATION",
        "head_sha": head_sha,
        "review_identities": review_identities,
        "openai_api_invocations": api_calls,
        "metered_api_on_routine_pull_request": False,
        "no_api_attestation_is_not_scientific_review": True,
        "scientific_review_gate": scientific_state,
    }


def coverage_truth(
    *,
    patch_percent: float | None,
    uncovered_changed_lines: int | None,
    informational: bool,
) -> dict[str, Any]:
    return {
        "artifact_type": "CYCLE30_COVERAGE_TRUTH",
        "patch_percent": patch_percent,
        "uncovered_changed_lines": uncovered_changed_lines,
        "informational": informational,
        "green_badge_is_not_requested_threshold": True,
        "global_100_not_claimed": True,
        "thresholds_restored": False,
    }

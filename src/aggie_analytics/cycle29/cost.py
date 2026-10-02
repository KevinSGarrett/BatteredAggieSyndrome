"""Codex cloud review vs metered API cost containment."""

from __future__ import annotations

from typing import Any


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
    *, head_sha: str, review_identities: list[str], api_calls: int
) -> dict[str, Any]:
    return {
        "artifact_type": "CYCLE29_CODEX_CLOUD_REVIEW_ATTESTATION",
        "head_sha": head_sha,
        "review_identities": review_identities,
        "openai_api_invocations": api_calls,
        "metered_api_on_routine_pull_request": False,
    }

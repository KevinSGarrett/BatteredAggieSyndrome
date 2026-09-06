"""Paid OpenAI PR-review cost containment. Does not operate the retired assistive plane."""

from __future__ import annotations

from typing import Any, Mapping

DEFAULT_MODEL = "gpt-5.3-codex"
DEFAULT_EFFORT = "low"
PREMIUM_MODELS = {"gpt-5.6-sol", "gpt-5.6-terra"}
SOFT_LIMIT_USD = 1.0
HARD_PR_LIMIT_USD = 3.0
HARD_CYCLE_LIMIT_USD = 10.0
READINESS_LABEL = "paid-scientific-review-ready"


class PaidReviewError(ValueError):
    """Raised when a paid review cannot be admitted."""


def review_tuple(
    *,
    repository: str,
    pr_number: int,
    base_sha: str,
    head_sha: str,
    merge_sha: str,
    changed_file_digest: str,
    prompt_sha256: str,
    rules_sha256: str,
    model: str,
    effort: str,
) -> tuple[Any, ...]:
    return (
        repository,
        int(pr_number),
        base_sha,
        head_sha,
        merge_sha,
        changed_file_digest,
        prompt_sha256,
        rules_sha256,
        model,
        effort,
    )


def admit_paid_review(
    *,
    deterministic_passed: bool,
    readiness_label_present: bool,
    authorized_head_sha: str,
    current_head_sha: str,
    model: str,
    effort: str,
    premium_authorized: bool,
    cache_hit: bool,
    prior_tuple_paid: bool,
    estimated_or_actual_cost_usd: float | None,
    pr_spend_usd: float,
    cycle_spend_usd: float,
    second_run: bool,
    second_run_reason: str | None,
    retry_loop: bool,
    raw_lake_or_secrets_in_prompt: bool,
) -> dict[str, Any]:
    if not deterministic_passed:
        raise PaidReviewError("deterministic CI/scientific-reference checks must run before paid review")
    if not readiness_label_present:
        raise PaidReviewError("paid review requires paid-scientific-review-ready exact-SHA authorization")
    if authorized_head_sha != current_head_sha:
        raise PaidReviewError("new push invalidates the paid-review authorization signal")
    if model in PREMIUM_MODELS and not premium_authorized:
        raise PaidReviewError("premium model requires explicit per-run user authorization")
    if model != DEFAULT_MODEL and model not in PREMIUM_MODELS:
        raise PaidReviewError(f"unsupported review model {model}")
    if effort not in {"low", "minimal", "none"} and not (effort == "medium" and premium_authorized):
        if effort != DEFAULT_EFFORT:
            raise PaidReviewError("default effort must be low/minimum supported")
    if prior_tuple_paid or cache_hit:
        raise PaidReviewError("identical review tuple must never be paid twice")
    if retry_loop:
        raise PaidReviewError("failed paid action has no automatic retry loop")
    if second_run and not second_run_reason:
        raise PaidReviewError("second paid review for one PR requires a reason receipt")
    if raw_lake_or_secrets_in_prompt:
        raise PaidReviewError("raw lake/Jira/private All-22/secrets cannot be sent")
    if estimated_or_actual_cost_usd is None:
        raise PaidReviewError("COST_UNKNOWN_FAIL_CLOSED: unknown cost cannot be treated as zero")
    projected_pr = pr_spend_usd + estimated_or_actual_cost_usd
    projected_cycle = cycle_spend_usd + estimated_or_actual_cost_usd
    if projected_pr > HARD_PR_LIMIT_USD or projected_cycle > HARD_CYCLE_LIMIT_USD:
        raise PaidReviewError("paid review would exceed a cost ceiling")
    return {
        "admitted": True,
        "model": model,
        "effort": effort,
        "cache_hit": False,
        "soft_warning": estimated_or_actual_cost_usd >= SOFT_LIMIT_USD,
        "human_dashboard_budget_action": "RECORDED_AS_HUMAN_ACTION",
    }

"""Normalized latest-head review gate.

GitHub can treat skipped or neutral required-check conclusions as passing.
This gate does not. Only an explicit success conclusion on the exact head SHA
counts. coverage-upload success is not Codecov patch/threshold success.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

SUCCESS = "success"
REJECTED_CONCLUSIONS = frozenset(
    {
        "",
        "skipped",
        "neutral",
        "failure",
        "cancelled",
        "timed_out",
        "stale",
        "action_required",
    }
)
REQUIRED_NAMED_CHECKS = (
    "codex-review",
    "codecov/patch",
)


class NormalizedReviewGateError(ValueError):
    """Raised when latest-head review evidence is not a successful merge defense."""


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def classify_check_conclusion(conclusion: Any) -> str:
    token = _norm(conclusion)
    if token == SUCCESS:
        return SUCCESS
    if token in REJECTED_CONCLUSIONS or not token:
        return "REJECTED_NOT_SUCCESS"
    return "REJECTED_UNKNOWN_CONCLUSION"


def evaluate_latest_head_checks(
    *,
    head_sha: str,
    checks: Sequence[Mapping[str, Any]],
    required_names: Sequence[str] = REQUIRED_NAMED_CHECKS,
) -> dict[str, Any]:
    if not head_sha or len(head_sha) < 40:
        raise NormalizedReviewGateError("HEAD_SHA_MISSING_OR_SHORT")
    by_name: dict[str, dict[str, Any]] = {}
    for raw in checks:
        name = str(raw.get("name") or "").strip()
        sha = str(raw.get("head_sha") or raw.get("sha") or "").strip()
        if sha and sha != head_sha:
            continue
        conclusion = raw.get("conclusion")
        classified = classify_check_conclusion(conclusion)
        prior = by_name.get(name)
        if prior is None or classified == SUCCESS:
            by_name[name] = {
                "name": name,
                "conclusion": conclusion,
                "classified": classified,
                "head_sha": sha or head_sha,
            }
    missing = [name for name in required_names if name not in by_name]
    unsuccessful = [
        name
        for name in required_names
        if name in by_name and by_name[name]["classified"] != SUCCESS
    ]
    coverage_upload_ok = by_name.get("coverage-upload", {}).get("classified") == SUCCESS
    codecov_ok = by_name.get("codecov/patch", {}).get("classified") == SUCCESS
    findings: list[str] = []
    if missing:
        findings.append("MISSING_REQUIRED_LATEST_HEAD_CHECK:" + ",".join(missing))
    if unsuccessful:
        findings.append("REQUIRED_CHECK_NOT_SUCCESS:" + ",".join(unsuccessful))
    if coverage_upload_ok and not codecov_ok:
        findings.append("COVERAGE_UPLOAD_IS_NOT_CODECOV_THRESHOLD")
    return {
        "ok": not findings,
        "head_sha": head_sha,
        "findings": findings,
        "coverage_upload_success_is_not_codecov": True,
        "skipped_or_neutral_are_not_success": True,
        "required_names": list(required_names),
        "observed": {name: by_name.get(name) for name in required_names},
    }

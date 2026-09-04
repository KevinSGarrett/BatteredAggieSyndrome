"""Normalized latest-head review gate.

GitHub can treat skipped or neutral required-check conclusions as passing.
This gate does not. Only an explicit success conclusion on the exact head SHA
counts. coverage-upload success is not Codecov patch/threshold success.
"""

from __future__ import annotations

import re
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
HEAD_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
INCOMPLETE_STATUSES = frozenset(
    {"in_progress", "queued", "pending", "waiting", "requested", "waiting_for_change"}
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


def _observed_sha(raw: Mapping[str, Any]) -> str:
    primary = str(raw.get("head_sha") or "").strip()
    if HEAD_SHA_RE.fullmatch(primary):
        return primary
    alternate = str(raw.get("sha") or "").strip()
    if HEAD_SHA_RE.fullmatch(alternate):
        return alternate
    return ""


def _attempt_recency(raw: Mapping[str, Any]) -> str:
    status = str(raw.get("status") or "").strip().casefold()
    incomplete = status in INCOMPLETE_STATUSES
    started = str(raw.get("started_at") or "")
    completed = str(raw.get("completed_at") or "")
    recency = started or completed
    if incomplete and not recency:
        return "9999-12-31T23:59:59Z"
    return recency


def _attempt_sort_key(raw: Mapping[str, Any]) -> tuple[str, str, str]:
    status = str(raw.get("status") or "").strip().casefold()
    incomplete = "1" if status in INCOMPLETE_STATUSES else "0"
    return (_attempt_recency(raw), incomplete, str(raw.get("id") or ""))


def evaluate_latest_head_checks(
    *,
    head_sha: str,
    checks: Sequence[Mapping[str, Any]],
    required_names: Sequence[str] = REQUIRED_NAMED_CHECKS,
) -> dict[str, Any]:
    if not HEAD_SHA_RE.fullmatch(str(head_sha or "")):
        raise NormalizedReviewGateError("HEAD_SHA_MISSING_OR_SHORT")
    findings: list[str] = []
    candidates: dict[str, list[Mapping[str, Any]]] = {
        name: [] for name in required_names
    }
    coverage_rows: list[Mapping[str, Any]] = []
    for raw in checks:
        name = str(raw.get("name") or "").strip()
        observed = _observed_sha(raw)
        if name in required_names and not observed:
            findings.append(f"REQUIRED_CHECK_MISSING_HEAD_SHA:{name}")
            continue
        if observed != head_sha:
            continue
        if name in candidates:
            candidates[name].append(raw)
        if name == "coverage-upload":
            coverage_rows.append(raw)
    by_name: dict[str, dict[str, Any]] = {}
    for name in required_names:
        rows = list(candidates[name])
        if not rows:
            continue
        rows.sort(key=_attempt_sort_key)
        latest_time = _attempt_recency(rows[-1])
        tied = [row for row in rows if _attempt_recency(row) == latest_time]
        classified_set = {
            classify_check_conclusion(row.get("conclusion")) for row in tied
        }
        if len(tied) > 1 and len(classified_set) > 1:
            findings.append(f"REQUIRED_CHECK_AMBIGUOUS_DUPLICATE:{name}")
        chosen = rows[-1]
        status = str(chosen.get("status") or "").strip().casefold()
        if status in INCOMPLETE_STATUSES:
            findings.append(f"REQUIRED_CHECK_NOT_COMPLETED:{name}")
        app = chosen.get("app")
        app_slug = app.get("slug") if isinstance(app, Mapping) else app
        by_name[name] = {
            "name": name,
            "conclusion": chosen.get("conclusion"),
            "classified": classify_check_conclusion(chosen.get("conclusion")),
            "head_sha": _observed_sha(chosen),
            "status": chosen.get("status"),
            "id": chosen.get("id"),
            "app": app_slug,
        }
    missing = [
        name
        for name in required_names
        if name not in by_name
        and not any(item.endswith(":" + name) for item in findings)
    ]
    unsuccessful = [
        name
        for name in required_names
        if name in by_name and by_name[name]["classified"] != SUCCESS
    ]
    coverage_latest = None
    if coverage_rows:
        coverage_rows.sort(key=_attempt_sort_key)
        coverage_latest = coverage_rows[-1]
    coverage_upload_ok = (
        classify_check_conclusion(coverage_latest.get("conclusion")) == SUCCESS
        if coverage_latest is not None
        else False
    )
    codecov_ok = by_name.get("codecov/patch", {}).get("classified") == SUCCESS
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

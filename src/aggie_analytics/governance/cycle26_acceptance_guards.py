"""Fail-closed Cycle #26 acceptance guards used by validators and tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

BLOCKED_PASS_TWO = frozenset(
    {"BLOCKED_INSUFFICIENT_EVIDENCE", "FAIL", "PARTIAL", "BLOCKED", "NOT_AUDITED_YET"}
)


def source_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def receipt_authorizes_head(receipt_head: str, live_head: str) -> bool:
    bound = str(receipt_head or "").strip().lower()
    live = str(live_head or "").strip().lower()
    if len(bound) != 40 or len(live) != 40:
        return False
    if any(ch not in "0123456789abcdef" for ch in bound + live):
        return False
    return bound == live


def capture_inventory_denominator(records: Sequence[Mapping[str, Any]]) -> int:
    """Manifest records, including CAPTURED_EMPTY, are the inventory count."""
    return len(list(records))


def nonempty_payload_file_count(records: Sequence[Mapping[str, Any]]) -> int:
    count = 0
    for row in records:
        raw = row.get("bytes")
        if raw is None:
            raw = row.get("byte_count")
        try:
            size = int(raw or 0)
        except (TypeError, ValueError):
            size = 0
        if size > 0:
            count += 1
    return count


def three_pass_complete_authorized(receipt: Mapping[str, Any]) -> bool:
    if str(receipt.get("result") or "") != "COMPLETE":
        return False
    evidence = receipt.get("pass_evidence") or []
    claims = [str(item) for item in (receipt.get("coverage_claims") or [])]
    if "category_search_only" in claims:
        return False
    if not evidence:
        return False
    return True


def semantically_audited_findings(
    cycle_number: object,
    *,
    claims: Sequence[Any] | None,
    passes: Mapping[str, Any],
    disposition: str,
) -> list[str]:
    if disposition != "SEMANTICALLY_AUDITED":
        return []
    findings: list[str] = []
    if not claims:
        findings.append(f"CLAIM_REGISTRY_EMPTY_OR_SEMANTICALLY_AUDITED:{cycle_number}")
    pass_two = str(passes.get("pass_two") or "")
    pass_three = str(passes.get("pass_three") or "")
    if pass_two in BLOCKED_PASS_TWO or pass_two == "BLOCKED":
        findings.append(
            f"SEMANTICALLY_AUDITED_WITH_BLOCKED_OR_PARTIAL_PASSES:{cycle_number}"
        )
    if pass_three != "COMPLETE":
        findings.append(
            f"SEMANTICALLY_AUDITED_WITH_BLOCKED_OR_PARTIAL_PASSES:{cycle_number}"
        )
    return findings


def scope_narrowing_authorized(
    original: Mapping[str, Any], narrowed: Mapping[str, Any]
) -> bool:
    if original.get("candidates") == narrowed.get("candidates") and original.get(
        "population"
    ) == narrowed.get("population"):
        return True
    return bool(narrowed.get("rationale")) and bool(
        narrowed.get("independent_approval")
    )


def apply_numeric_correctness(record: Mapping[str, Any]) -> dict[str, Any]:
    """Pair coherence must not open trust, merge, or credibility gates."""
    result = dict(record)
    result.setdefault("publication_label", "UNTRUSTED_SHADOW")
    result["ACTIVE_PATH_CORRECTNESS_CLAIM"] = bool(
        record.get("ACTIVE_PATH_CORRECTNESS_CLAIM")
    )
    result["ALL_CYCLE_SCIENTIFIC_TRUST_GATE"] = bool(
        record.get("ALL_CYCLE_SCIENTIFIC_TRUST_GATE")
    )
    result["merge_authorized"] = False
    result["production_credibility"] = False
    return result


def three_pass_authorizes_active_path(
    receipts: Mapping[str, Mapping[str, Any]],
) -> bool:
    pass_one = receipts.get("pass_1") or {}
    pass_three = receipts.get("pass_3") or {}
    if pass_one.get("dependencies_resolved") is not True:
        return False
    if str(pass_three.get("result") or "") not in {
        "PASS",
        "PASS_WITHIN_DECLARED_SCOPE",
    }:
        return False
    return True


def jira_convergence_verdict(
    *,
    local_validate: str | None,
    live_verify: str | None,
    board_pagination_complete: bool,
) -> str:
    if (
        local_validate == "PASS"
        and live_verify == "PASS"
        and board_pagination_complete is True
    ):
        return "VERIFIED"
    if local_validate == "PASS" and live_verify is None:
        return "PARTIAL"
    return "BLOCKED"


def concurrent_live_write_allowed(
    planned: Mapping[str, Any], live_reread: Mapping[str, Any]
) -> bool:
    return dict(planned) == dict(live_reread)


def all_abstention_or_control_sets_active_path_verified(
    claim: Mapping[str, Any],
) -> bool:
    if claim.get("all_abstention") or claim.get("control_only"):
        return False
    if int(claim.get("emitted_fitted") or 0) <= 0:
        return False
    return bool(claim.get("ACTIVE_PATH_CORRECTNESS_VERIFIED"))

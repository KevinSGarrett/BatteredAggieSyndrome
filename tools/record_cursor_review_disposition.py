from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.contracts import canonical_json_bytes  # noqa: E402
from aggie_analytics.assistive_plane.cursor_backend import cursor_agent_identity  # noqa: E402
from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json  # noqa: E402


DEFAULT_STORAGE_ROOT = Path(r"C:\BatteredAggieSyndrome.data\assistive\cursor")
ALLOWED_DISPOSITIONS = {
    "ACCEPTED",
    "ACCEPTED_WITH_CODEX_REVIEW_EDITS",
    "REVIEW_ONLY",
    "QUARANTINED",
    "REJECTED",
}
REQUIRED_REVIEW_FIELDS = {
    "schema_version",
    "jira_unit",
    "campaign_unit",
    "job_id",
    "agent_id",
    "cursor_branch",
    "cursor_commit",
    "integration_pr",
    "integration_commit",
    "disposition",
    "contribution",
    "codex_review_edits",
    "negative_findings",
    "local_validation",
    "review_started_at_utc",
    "review_completed_at_utc",
    "measured_review_and_orchestration_minutes",
    "direct_baseline_minutes",
}


def verified_content_addressed_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    import hashlib

    digest = hashlib.sha256(raw).hexdigest()
    if path.stem != digest:
        raise RuntimeError(f"CURSOR_EVIDENCE_CONTENT_ADDRESS_MISMATCH:{path}")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError(f"CURSOR_EVIDENCE_OBJECT_REQUIRED:{path}")
    return payload


def evidence_for_identity(root: Path, category: str, job_id: str, agent_id: str) -> list[tuple[Path, dict[str, Any]]]:
    category_root = root / category
    matched: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(category_root.rglob("*.json")) if category_root.is_dir() else []:
        payload = verified_content_addressed_json(path)
        if payload.get("job_id") == job_id and payload.get("agent_id") == agent_id:
            matched.append((path, payload))
    return matched


def git_ancestor(repository: Path, commit: str, main_ref: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repository), "merge-base", "--is-ancestor", commit, main_ref],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def git_subject(repository: Path, commit: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), "show", "-s", "--format=%s", commit],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _usage_amount(payload: dict[str, Any]) -> Decimal:
    return Decimal(str(payload.get("provider_aggregate_usd", "-1")))


def _settled_job_total(ledger: dict[str, Any], job_id: str) -> Decimal:
    import hashlib

    finalize_id = hashlib.sha256(f"{job_id}:finalize:v1".encode("utf-8")).hexdigest()
    settlements = ledger.get("settlements", {})
    return Decimal(str(settlements.get(job_id, "0"))) + Decimal(str(settlements.get(finalize_id, "0")))


def _validate_review_input(review: dict[str, Any]) -> None:
    if set(review) != REQUIRED_REVIEW_FIELDS:
        raise ValueError("CURSOR_REVIEW_FIELDS_INVALID")
    if review["schema_version"] != 1:
        raise ValueError("CURSOR_REVIEW_SCHEMA_VERSION_INVALID")
    if review["jira_unit"] != "POST-SUBTASK-202":
        raise ValueError("CURSOR_REVIEW_JIRA_UNIT_INVALID")
    if not isinstance(review["campaign_unit"], int) or review["campaign_unit"] <= 0:
        raise ValueError("CURSOR_REVIEW_CAMPAIGN_UNIT_INVALID")
    if not re.fullmatch(r"[0-9a-f]{64}", str(review["job_id"])):
        raise ValueError("CURSOR_REVIEW_JOB_ID_INVALID")
    if review["agent_id"] != cursor_agent_identity(review["job_id"]):
        raise ValueError("CURSOR_REVIEW_AGENT_JOB_IDENTITY_MISMATCH")
    if not re.fullmatch(r"[0-9a-f]{40}", str(review["cursor_commit"])):
        raise ValueError("CURSOR_REVIEW_CURSOR_COMMIT_INVALID")
    if not re.fullmatch(r"[0-9a-f]{40}", str(review["integration_commit"])):
        raise ValueError("CURSOR_REVIEW_INTEGRATION_COMMIT_INVALID")
    if not isinstance(review["integration_pr"], int) or review["integration_pr"] <= 0:
        raise ValueError("CURSOR_REVIEW_INTEGRATION_PR_INVALID")
    if review["disposition"] not in ALLOWED_DISPOSITIONS:
        raise ValueError("CURSOR_REVIEW_DISPOSITION_INVALID")
    for field in ("contribution", "codex_review_edits", "negative_findings"):
        if not isinstance(review[field], list) or not all(isinstance(item, str) and item.strip() for item in review[field]):
            raise ValueError(f"CURSOR_REVIEW_{field.upper()}_INVALID")
    if review["disposition"] == "ACCEPTED_WITH_CODEX_REVIEW_EDITS" and not review["codex_review_edits"]:
        raise ValueError("CURSOR_REVIEW_MODIFIED_REQUIRES_EDITS")
    if review["disposition"] == "ACCEPTED" and review["codex_review_edits"]:
        raise ValueError("CURSOR_REVIEW_ACCEPTED_CANNOT_RECORD_EDITS")
    if not isinstance(review["local_validation"], dict) or review["local_validation"].get("exit_code") != 0:
        raise ValueError("CURSOR_REVIEW_VALIDATION_NOT_PASSING")
    if review["direct_baseline_minutes"] is not None:
        baseline = float(review["direct_baseline_minutes"])
        if baseline < 0:
            raise ValueError("CURSOR_REVIEW_DIRECT_BASELINE_INVALID")


def record_review_disposition(
    review: dict[str, Any],
    *,
    storage_root: Path,
    repository: Path,
    main_ref: str = "origin/main",
    ancestry_checker: Callable[[Path, str, str], bool] = git_ancestor,
    subject_reader: Callable[[Path, str], str] = git_subject,
) -> tuple[Path, str, dict[str, Any]]:
    _validate_review_input(review)
    job_id = str(review["job_id"])
    agent_id = str(review["agent_id"])
    requests = evidence_for_identity(storage_root, "requests", job_id, agent_id)
    manifests = evidence_for_identity(storage_root, "manifests", job_id, agent_id)
    results = evidence_for_identity(storage_root, "results", job_id, agent_id)
    settlements = evidence_for_identity(storage_root, "settlements", job_id, agent_id)
    if not requests or not manifests or not results or not settlements:
        raise RuntimeError("CURSOR_REVIEW_REQUIRED_EVIDENCE_MISSING")

    initial = manifests[-1][1]
    if (
        initial.get("canonical_write_authority") is not False
        or initial.get("protected_decision_authority") is not False
        or initial.get("auto_create_pr") is not False
        or initial.get("work_on_current_branch") is not False
        or initial.get("jira_unit") != review["jira_unit"]
    ):
        raise RuntimeError("CURSOR_REVIEW_AUTHORITY_BOUNDARY_INVALID")
    base_commit = str(initial.get("base_commit", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", base_commit):
        raise RuntimeError("CURSOR_REVIEW_BASE_COMMIT_MISSING")

    final_settlement_path, final_settlement = max(settlements, key=lambda item: _usage_amount(item[1]))
    aggregate_usd = _usage_amount(final_settlement)
    if aggregate_usd <= 0 or final_settlement.get("reservation_resolved") is not True:
        raise RuntimeError("CURSOR_REVIEW_SETTLEMENT_INCOMPLETE")
    ledger_path = storage_root / "usage" / "ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if _settled_job_total(ledger, job_id) != aggregate_usd:
        raise RuntimeError("CURSOR_REVIEW_LEDGER_SETTLEMENT_MISMATCH")

    result_sha256 = str(final_settlement.get("result_sha256", ""))
    final_results = [(path, payload) for path, payload in results if path.stem == result_sha256]
    if len(final_results) != 1:
        raise RuntimeError("CURSOR_REVIEW_SETTLED_RESULT_MISSING")
    final_result = final_results[0][1]
    if final_result.get("run", {}).get("status") != "FINISHED":
        raise RuntimeError("CURSOR_REVIEW_TERMINAL_RESULT_REQUIRED")
    result_text = str(final_result.get("run", {}).get("result", ""))
    branches = {
        str(item.get("branch"))
        for item in final_result.get("run", {}).get("git", {}).get("branches", [])
        if item.get("branch")
    }
    if review["cursor_branch"] not in branches or review["cursor_commit"] not in result_text:
        raise RuntimeError("CURSOR_REVIEW_BRANCH_COMMIT_EVIDENCE_MISMATCH")
    if not ancestry_checker(repository, str(review["integration_commit"]), main_ref):
        raise RuntimeError("CURSOR_REVIEW_INTEGRATION_NOT_ON_MAIN")
    if f"(#{review['integration_pr']})" not in subject_reader(repository, str(review["integration_commit"])):
        raise RuntimeError("CURSOR_REVIEW_PR_MERGE_IDENTITY_MISMATCH")

    usage = final_settlement.get("provider_usage", {}).get("totalUsage", {})
    run_ids = sorted(
        {
            str(item.get("id"))
            for item in final_settlement.get("provider_usage", {}).get("runs", [])
            if item.get("id")
        }
    )
    disposition = str(review["disposition"])
    accepted = int(disposition in {"ACCEPTED", "ACCEPTED_WITH_CODEX_REVIEW_EDITS"})
    modified = int(disposition == "ACCEPTED_WITH_CODEX_REVIEW_EDITS")
    review_only = int(disposition == "REVIEW_ONLY")
    quarantined = int(disposition == "QUARANTINED")
    rejected = int(disposition == "REJECTED")
    direct_baseline = review["direct_baseline_minutes"]
    review_record = {
        "schema_version": 2,
        "artifact_type": "CURSOR_REAL_REPOSITORY_UNIT_REVIEW_DISPOSITION",
        "jira_unit": review["jira_unit"],
        "campaign_unit": review["campaign_unit"],
        "job_id": job_id,
        "agent_id": agent_id,
        "base_commit": base_commit,
        "cursor_branch": review["cursor_branch"],
        "cursor_commit": review["cursor_commit"],
        "integration_pr": review["integration_pr"],
        "integration_commit": review["integration_commit"],
        "model": initial.get("model"),
        "reasoning": initial.get("reasoning"),
        "fast": initial.get("fast"),
        "run_ids": run_ids,
        "provider_usage": {
            "input_tokens": int(usage.get("inputTokens", 0)),
            "output_tokens": int(usage.get("outputTokens", 0)),
            "cache_read_tokens": int(usage.get("cacheReadTokens", 0)),
            "cache_write_tokens": int(usage.get("cacheWriteTokens", 0)),
            "total_tokens": int(usage.get("totalTokens", 0)),
            "actual_usd": format(aggregate_usd, "f"),
        },
        "disposition": disposition,
        "accepted_useful_results": accepted,
        "modified_results": modified,
        "review_only_results": review_only,
        "quarantined_results": quarantined,
        "rejected_results": rejected,
        "provider_failures": 0,
        "contribution": review["contribution"],
        "codex_review_edits": review["codex_review_edits"],
        "negative_findings": review["negative_findings"],
        "local_validation": review["local_validation"],
        "review_started_at_utc": review["review_started_at_utc"],
        "review_completed_at_utc": review["review_completed_at_utc"],
        "measured_review_and_orchestration_minutes": review["measured_review_and_orchestration_minutes"],
        "direct_baseline_minutes": direct_baseline,
        "measured_effective_savings_minutes": None,
        "savings_claim": "NOT_ESTABLISHED_WITHOUT_A_MEASURED_DIRECT_BASELINE" if direct_baseline is None else "REQUIRES_INDEPENDENT_CALCULATION",
        "dispatch_origin": "TRANSITIONAL_CURSOR_CLI_CONTROLLER",
        "candidate_only": True,
        "canonical_authority": False,
        "protected_authority": False,
        "scientific_claim": False,
        "evidence": {
            "request_sha256s": [path.stem for path, _ in requests],
            "manifest_sha256s": [path.stem for path, _ in manifests],
            "result_sha256": result_sha256,
            "settlement_sha256s": [path.stem for path, _ in settlements],
            "final_settlement_sha256": final_settlement_path.stem,
            "ledger_sha256": __import__("hashlib").sha256(ledger_path.read_bytes()).hexdigest(),
            "integration_ancestor_ref": main_ref,
        },
    }
    prior_reviews = evidence_for_identity(storage_root, "dispositions", job_id, agent_id)
    if prior_reviews:
        exact = [(path, payload) for path, payload in prior_reviews if payload == review_record]
        if len(prior_reviews) == 1 and len(exact) == 1:
            return exact[0][0], exact[0][0].stem, review_record
        raise RuntimeError("CURSOR_REVIEW_DUPLICATE_DISPOSITION_IDENTITY")
    path, digest = write_content_addressed_json(storage_root, "dispositions", review_record)
    return path, digest, review_record


def main() -> int:
    parser = argparse.ArgumentParser(description="Record one evidence-bound Cursor review disposition")
    parser.add_argument("review", type=Path)
    parser.add_argument("--storage-root", type=Path, default=DEFAULT_STORAGE_ROOT)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--main-ref", default="origin/main")
    args = parser.parse_args()
    review = json.loads(args.review.read_text(encoding="utf-8"))
    path, digest, record = record_review_disposition(
        review,
        storage_root=args.storage_root,
        repository=args.repository,
        main_ref=args.main_ref,
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "campaign_unit": record["campaign_unit"],
                "disposition": record["disposition"],
                "path": str(path),
                "sha256": digest,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

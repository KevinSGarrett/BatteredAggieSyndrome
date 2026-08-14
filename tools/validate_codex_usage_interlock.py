"""Fail-closed validator for direct-Codex work and independent pipeline proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "instructions/policies/assistive_execution_interlock.json"
CHANGE_MANIFEST_PATH = ROOT / "configs/codex_usage_interlock_change_manifest.json"
BINDING_PATH = ROOT / "configs/unified_assistive_change_routing_binding.json"
DEFAULT_RUNTIME_ROOT = Path(r"C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3")

REQUIRED_MARKER = "P0 fail-closed assistive-execution interlock"
REQUIRED_HANDOFF = (
    "UNIFIED ASSISTIVE PLANE: NOT OPERATIONAL — CONTINUOUS REAL-WORK PRODUCTION, "
    "AUTONOMOUS PROVIDER ROUTING, AND NON-BYPASSABLE CODEX FALLBACK CONTROL HAVE NOT YET BEEN PROVEN."
)


def _load_json(path: Path, findings: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exact parser error is evidence
        findings.append(f"INVALID_JSON:{path.as_posix()}:{type(exc).__name__}")
        return {}
    if not isinstance(value, dict):
        findings.append(f"INVALID_JSON_ROOT:{path.as_posix()}")
        return {}
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative(path: str) -> bool:
    candidate = PurePosixPath(path)
    return bool(path) and "\\" not in path and not candidate.is_absolute() and ".." not in candidate.parts


def _matches_prefix(path: str, allowed: list[str]) -> bool:
    for prefix in allowed:
        if prefix.endswith("/") and path.startswith(prefix):
            return True
        if prefix.endswith("_") and path.startswith(prefix):
            return True
        if path == prefix:
            return True
    return False


def _canonical_identity(payload: dict[str, Any]) -> str:
    identity_payload = dict(payload)
    identity_payload.pop("manifest_identity", None)
    encoded = json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_change_binding(
    policy: dict[str, Any],
    manifest: dict[str, Any],
    binding: dict[str, Any],
    findings: list[str],
) -> None:
    work_class = binding.get("class")
    if manifest.get("work_class") != work_class:
        findings.append("CHANGE_MANIFEST_BINDING_CLASS_MISMATCH")
    if manifest.get("ordinary_project_work_authorized") is not False:
        findings.append("CHANGE_MANIFEST_AUTHORIZES_ORDINARY_DIRECT_WORK")
    if binding.get("ordinary_project_work_authorized") is not False:
        findings.append("CHANGE_BINDING_AUTHORIZES_ORDINARY_DIRECT_WORK")
    if manifest.get("pre_routing_decision_sha256") != binding.get("decision_sha256"):
        findings.append("CHANGE_MANIFEST_BINDING_IDENTITY_MISMATCH")
    if not _valid_sha256(binding.get("decision_sha256")):
        findings.append("CHANGE_BINDING_DECISION_IDENTITY_INVALID")

    changed = manifest.get("changed_paths", [])
    if not isinstance(changed, list) or not changed:
        findings.append("CHANGE_MANIFEST_PATHS_MISSING")
        changed = []
    for path in changed:
        if not isinstance(path, str) or not _safe_relative(path):
            findings.append(f"CHANGE_MANIFEST_PATH_INVALID:{path}")
    if len(changed) != len(set(changed)):
        findings.append("CHANGE_MANIFEST_DUPLICATE_PATH")
    if manifest.get("work_unit_id") != binding.get("work_unit_id"):
        findings.append("CHANGE_MANIFEST_BINDING_WORK_UNIT_MISMATCH")
    if manifest.get("jira_identity") != binding.get("jira_identity"):
        findings.append("CHANGE_MANIFEST_BINDING_JIRA_IDENTITY_MISMATCH")
    if manifest.get("base_commit") != binding.get("source_commit"):
        findings.append("CHANGE_MANIFEST_BINDING_SOURCE_COMMIT_MISMATCH")

    if work_class == "PIPELINE_BOOTSTRAP_REPAIR":
        if binding.get("disposition") != "EMERGENCY_PIPELINE_REPAIR":
            findings.append("BOOTSTRAP_REPAIR_DISPOSITION_INVALID")
        allowed = policy.get("bootstrap_allowed_paths", [])
        for path in changed:
            if isinstance(path, str) and _safe_relative(path) and not _matches_prefix(path, allowed):
                findings.append(f"NON_BOOTSTRAP_PATH_WHILE_INTERLOCK_CLOSED:{path}")
        return

    if work_class != "PROJECT_WORK":
        findings.append(f"UNSUPPORTED_CHANGE_BINDING_CLASS:{work_class}")
        return

    adoption_policy = policy.get("routed_project_adoption", {})
    adoption = binding.get("routed_project_adoption", {})
    if not isinstance(adoption, dict):
        findings.append("ROUTED_PROJECT_ADOPTION_EVIDENCE_MISSING")
        return
    if binding.get("disposition") != "ROUTED_TO_ASSISTIVE_PLANE":
        findings.append("PROJECT_WORK_NOT_ROUTED_TO_ASSISTIVE_PLANE")
    if adoption.get("dispatch_origin") != adoption_policy.get("required_dispatch_origin"):
        findings.append("PROJECT_WORK_NOT_PERSISTENT_CONTROLLER_ROUTED")
    if adoption.get("manual_or_session_initiated") is not False:
        findings.append("PROJECT_WORK_MANUAL_DISPATCH_FORBIDDEN")
    if adoption.get("unjustified_direct_execution") is not False:
        findings.append("PROJECT_WORK_UNJUSTIFIED_DIRECT_EXECUTION")
    if adoption.get("provider_result_disposition") not in adoption_policy.get(
        "permitted_provider_result_dispositions", []
    ):
        findings.append("PROJECT_WORK_PROVIDER_RESULT_DISPOSITION_INVALID")
    if adoption.get("final_disposition") not in adoption_policy.get(
        "permitted_final_dispositions", []
    ):
        findings.append("PROJECT_WORK_FINAL_DISPOSITION_INVALID")
    if (
        adoption.get("provider_result_disposition") == "REVIEW_ONLY"
        and adoption.get("final_disposition") != "CODEX_REVIEW_MODIFIED"
    ):
        findings.append("REVIEW_ONLY_RESULT_REQUIRES_EXPLICIT_CODEX_MODIFICATION_DISPOSITION")
    for field in adoption_policy.get("required_sha256_fields", []):
        if not _valid_sha256(adoption.get(field)):
            findings.append(f"PROJECT_WORK_EVIDENCE_IDENTITY_INVALID:{field}")
    for field in adoption_policy.get("required_route_fields", []):
        if not isinstance(adoption.get(field), str) or not adoption.get(field):
            findings.append(f"PROJECT_WORK_ROUTE_FIELD_MISSING:{field}")
    if not isinstance(adoption.get("downstream_consumer"), str) or not adoption.get(
        "downstream_consumer"
    ):
        findings.append("PROJECT_WORK_DOWNSTREAM_CONSUMER_MISSING")
    if not isinstance(adoption.get("cleanup_contract"), str) or not adoption.get(
        "cleanup_contract"
    ):
        findings.append("PROJECT_WORK_CLEANUP_CONTRACT_MISSING")
    if not isinstance(adoption.get("codex_modifications"), list) or not adoption.get(
        "codex_modifications"
    ):
        findings.append("PROJECT_WORK_CODEX_MODIFICATION_SCOPE_MISSING")

    allowed_paths = binding.get("allowed_paths", [])
    if not isinstance(allowed_paths, list) or not allowed_paths:
        findings.append("PROJECT_WORK_ALLOWED_PATHS_MISSING")
        allowed_paths = []
    for path in allowed_paths:
        if not isinstance(path, str) or not _safe_relative(path):
            findings.append(f"PROJECT_WORK_ALLOWED_PATH_INVALID:{path}")
    if len(allowed_paths) != len(set(allowed_paths)):
        findings.append("PROJECT_WORK_ALLOWED_PATH_DUPLICATE")
    unlisted = sorted(set(changed) - set(allowed_paths))
    if unlisted:
        findings.append("PROJECT_WORK_PATH_OUTSIDE_ROUTED_ALLOWLIST:" + ",".join(unlisted))
    if sorted(allowed_paths) != sorted(changed):
        findings.append("PROJECT_WORK_ROUTED_ALLOWLIST_NOT_EXACT_CHANGE_SET")


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise RuntimeError(f"GIT_COMMAND_FAILED:{' '.join(args)}:{completed.stderr.strip()}")
    return completed.stdout


def _changed_paths(mode: str, manifest: dict[str, Any], findings: list[str]) -> list[str]:
    try:
        if mode == "pre-commit":
            output = _git("diff", "--cached", "--name-only", "--diff-filter=ACMRD")
        else:
            base = os.environ.get("GITHUB_BASE_REF")
            if base:
                base_ref = f"origin/{base}"
            else:
                base_ref = str(manifest.get("base_commit", ""))
            if len(base_ref) == 40:
                output = _git("diff", "--name-only", "--diff-filter=ACMRD", f"{base_ref}...HEAD")
            else:
                merge_base = _git("merge-base", "origin/main", "HEAD").strip()
                output = _git("diff", "--name-only", "--diff-filter=ACMRD", f"{merge_base}...HEAD")
    except RuntimeError as exc:
        findings.append(str(exc))
        return []
    return sorted({line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()})


def _validate_static(findings: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    policy = _load_json(POLICY_PATH, findings)
    manifest = _load_json(CHANGE_MANIFEST_PATH, findings)
    binding = _load_json(BINDING_PATH, findings)

    if policy.get("schema_version") != 2 or policy.get("version") != "3.1.0":
        findings.append("INTERLOCK_POLICY_IDENTITY_INVALID")
    if policy.get("runtime_state") != "NOT_OPERATIONAL":
        findings.append("INTERLOCK_SELF_PROMOTION_FORBIDDEN")
    if policy.get("codex_project_work_allowed") is not False:
        findings.append("CODEX_PROJECT_WORK_MUST_FAIL_CLOSED")
    for key in (
        "empty_queue_authorizes_fallback",
        "provider_failure_authorizes_fallback",
        "self_promotion_allowed",
    ):
        if policy.get(key) is not False:
            findings.append(f"INTERLOCK_BOOLEAN_MUST_BE_FALSE:{key}")
    required_unlock = {
        "INDEPENDENT_TWO_HOUR_BLACK_BOX_PASS",
        "TWENTY_FOUR_HOUR_PROBATION_PASS",
        "SEVEN_DAY_SUSTAINED_OPERATION_PASS",
        "ZERO_UNJUSTIFIED_DIRECT_EXECUTION",
        "POSITIVE_DOWNSTREAM_CONSUMED_USEFUL_OFFLOAD",
        "POSITIVE_MEASURED_NET_TIME_SAVED",
        "INDEPENDENT_AUDITOR_PASS",
    }
    if not required_unlock.issubset(set(policy.get("unlock_requires", []))):
        findings.append("INTERLOCK_UNLOCK_REQUIREMENTS_INCOMPLETE")
    adoption_policy = policy.get("routed_project_adoption", {})
    if adoption_policy.get("required_dispatch_origin") != "PERSISTENT_CONTROLLER":
        findings.append("ROUTED_PROJECT_POLICY_DISPATCH_ORIGIN_INVALID")
    if adoption_policy.get("manual_dispatch_allowed") is not False:
        findings.append("ROUTED_PROJECT_POLICY_MANUAL_DISPATCH_MUST_BE_FALSE")
    if adoption_policy.get("unjustified_direct_execution_allowed") is not False:
        findings.append("ROUTED_PROJECT_POLICY_DIRECT_EXECUTION_MUST_BE_FALSE")
    if set(adoption_policy.get("permitted_provider_result_dispositions", [])) != {
        "ACCEPTED",
        "REVIEW_ONLY",
    }:
        findings.append("ROUTED_PROJECT_POLICY_PROVIDER_DISPOSITIONS_INVALID")
    if set(adoption_policy.get("permitted_final_dispositions", [])) != {
        "ACCEPTED",
        "CODEX_REVIEW_MODIFIED",
    }:
        findings.append("ROUTED_PROJECT_POLICY_FINAL_DISPOSITIONS_INVALID")
    if set(adoption_policy.get("required_sha256_fields", [])) != {
        "provider_request_sha256",
        "provider_result_sha256",
        "provider_review_sha256",
        "route_identity",
        "schema_identity",
        "policy_identity",
    }:
        findings.append("ROUTED_PROJECT_POLICY_EVIDENCE_IDENTITIES_INCOMPLETE")
    if set(adoption_policy.get("required_route_fields", [])) != {
        "provider",
        "model",
        "task_format",
    }:
        findings.append("ROUTED_PROJECT_POLICY_ROUTE_FIELDS_INCOMPLETE")
    epistemic = policy.get("epistemic_boundary", {})
    if epistemic.get("billing_motive_claim_allowed") is not False:
        findings.append("HIDDEN_BILLING_MOTIVE_CLAIM_MUST_REMAIN_FORBIDDEN")

    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    instruction = (ROOT / "instructions/25_FORT_KNOX_ASSISTIVE_EXECUTION_INTERLOCK.md").read_text(
        encoding="utf-8"
    )
    start = (ROOT / "instructions/START_HERE.md").read_text(encoding="utf-8")
    state = (ROOT / "governance/CURRENT_STATE.yaml").read_text(encoding="utf-8")
    if REQUIRED_MARKER not in agents:
        findings.append("AGENTS_INTERLOCK_MARKER_MISSING")
    if REQUIRED_HANDOFF not in instruction:
        findings.append("MANDATORY_HANDOFF_LANGUAGE_MISSING")
    if "25_FORT_KNOX_ASSISTIVE_EXECUTION_INTERLOCK.md" not in start:
        findings.append("START_HERE_INTERLOCK_POINTER_MISSING")
    if "assistive_operational_state: NOT_OPERATIONAL" not in state:
        findings.append("CURRENT_STATE_MUST_REMAIN_NOT_OPERATIONAL")

    expected_manifest_identity = _canonical_identity(manifest)
    if manifest.get("manifest_identity") != expected_manifest_identity:
        findings.append(
            f"CHANGE_MANIFEST_IDENTITY_MISMATCH:{manifest.get('manifest_identity')}!={expected_manifest_identity}"
        )
    _validate_change_binding(policy, manifest, binding, findings)
    return policy, manifest


def _validate_change_set(mode: str, manifest: dict[str, Any], findings: list[str]) -> None:
    actual = _changed_paths(mode, manifest, findings)
    # A pre-commit invocation with no staged paths is a static integrity check,
    # not a replay of the most recently merged immutable change manifest.  The
    # hook is also invoked explicitly during clean-tree validation and must not
    # manufacture a mismatch from historical evidence.  Any staged path keeps
    # the exact fail-closed equality check below.
    if mode == "pre-commit" and not actual:
        return
    expected = sorted(manifest.get("changed_paths", []))
    if actual != expected:
        findings.append(
            "CHANGE_MANIFEST_DIFF_MISMATCH:"
            + json.dumps({"actual": actual, "expected": expected}, separators=(",", ":"))
        )


def _validate_runtime(runtime_root: Path, findings: list[str]) -> dict[str, Any]:
    proof_contracts = {
        "black_box": (runtime_root / "black-box/current.json", 7200),
        "probation": (runtime_root / "probation/current.json", 86400),
        "soak": (runtime_root / "soak/current.json", 7 * 86400),
        "independent_auditor": (runtime_root / "completeness/current.json", 0),
    }
    evidence: dict[str, Any] = {}
    for name, (path, minimum_seconds) in proof_contracts.items():
        if not path.is_file():
            findings.append(f"RUNTIME_PROOF_MISSING:{name}:{path}")
            continue
        value = _load_json(path, findings)
        evidence[name] = {"path": str(path), "sha256": _sha256(path), "payload": value}
        if value.get("result") != "PASS":
            findings.append(f"RUNTIME_PROOF_NOT_PASS:{name}")
        if minimum_seconds and float(value.get("duration_seconds", 0)) < minimum_seconds:
            findings.append(f"RUNTIME_PROOF_DURATION_SHORT:{name}")
        if value.get("codex_interventions", 1) != 0:
            findings.append(f"RUNTIME_PROOF_CODEX_INTERVENTION:{name}")
        if value.get("manual_packet_replenishments", 1) != 0:
            findings.append(f"RUNTIME_PROOF_MANUAL_REPLENISHMENT:{name}")
        if value.get("unjustified_direct_execution", 1) != 0:
            findings.append(f"RUNTIME_PROOF_DIRECT_BYPASS:{name}")
    black_box = evidence.get("black_box", {}).get("payload", {})
    if int(black_box.get("downstream_consumed_useful_outputs", 0)) <= 0:
        findings.append("BLACK_BOX_NO_DOWNSTREAM_CONSUMED_USEFUL_OUTPUT")
    if float(black_box.get("measured_net_time_saved_seconds", 0)) <= 0:
        findings.append("BLACK_BOX_NO_POSITIVE_MEASURED_SAVINGS")
    # Absence of the black-box proof is already a hard failure above.  Do not
    # misreport that absence as a positive identity mismatch; only evidence
    # that actually exists can assert or falsify the identity binding.
    if black_box and black_box.get("exact_main_deployed_identity_match") is not True:
        findings.append("BLACK_BOX_EXACT_MAIN_DEPLOYMENT_MISMATCH")
    return evidence


def validate(mode: str, runtime_root: Path) -> dict[str, Any]:
    findings: list[str] = []
    policy, manifest = _validate_static(findings)
    if mode in {"pre-commit", "ci"}:
        _validate_change_set(mode, manifest, findings)
    runtime_evidence: dict[str, Any] = {}
    if mode == "runtime":
        runtime_evidence = _validate_runtime(runtime_root, findings)
    result = "PASS" if not findings else "FAIL"
    return {
        "validator": "codex_usage_interlock",
        "mode": mode,
        "result": result,
        "runtime_state": policy.get("runtime_state", "UNKNOWN"),
        "codex_project_work_allowed": policy.get("codex_project_work_allowed", False),
        "change_manifest_identity": manifest.get("manifest_identity"),
        "findings": findings,
        "runtime_evidence": runtime_evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("static", "pre-commit", "ci", "runtime"), default="static")
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    args = parser.parse_args()
    report = validate(args.mode, args.runtime_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

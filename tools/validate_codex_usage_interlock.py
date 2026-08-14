from __future__ import annotations

"""Fail-closed validator for direct-Codex work and independent pipeline proof."""

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

    if policy.get("schema_version") != 2 or policy.get("version") != "3.0.0":
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

    if binding.get("class") != "PIPELINE_BOOTSTRAP_REPAIR":
        findings.append("CHANGE_BINDING_NOT_BOOTSTRAP_REPAIR")
    if binding.get("ordinary_project_work_authorized") is not False:
        findings.append("CHANGE_BINDING_AUTHORIZES_ORDINARY_PROJECT_WORK")
    if manifest.get("work_class") != "PIPELINE_BOOTSTRAP_REPAIR":
        findings.append("CHANGE_MANIFEST_NOT_BOOTSTRAP_REPAIR")
    if manifest.get("ordinary_project_work_authorized") is not False:
        findings.append("CHANGE_MANIFEST_AUTHORIZES_ORDINARY_PROJECT_WORK")
    if manifest.get("pre_routing_decision_sha256") != binding.get("decision_sha256"):
        findings.append("CHANGE_MANIFEST_BINDING_IDENTITY_MISMATCH")
    expected_manifest_identity = _canonical_identity(manifest)
    if manifest.get("manifest_identity") != expected_manifest_identity:
        findings.append(
            f"CHANGE_MANIFEST_IDENTITY_MISMATCH:{manifest.get('manifest_identity')}!={expected_manifest_identity}"
        )
    changed = manifest.get("changed_paths", [])
    if not isinstance(changed, list) or not changed:
        findings.append("CHANGE_MANIFEST_PATHS_MISSING")
        changed = []
    allowed = policy.get("bootstrap_allowed_paths", [])
    for path in changed:
        if not isinstance(path, str) or not _safe_relative(path):
            findings.append(f"CHANGE_MANIFEST_PATH_INVALID:{path}")
        elif not _matches_prefix(path, allowed):
            findings.append(f"NON_BOOTSTRAP_PATH_WHILE_INTERLOCK_CLOSED:{path}")
    if len(changed) != len(set(changed)):
        findings.append("CHANGE_MANIFEST_DUPLICATE_PATH")
    return policy, manifest


def _validate_change_set(mode: str, manifest: dict[str, Any], findings: list[str]) -> None:
    actual = _changed_paths(mode, manifest, findings)
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
    if black_box.get("exact_main_deployed_identity_match") is not True:
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

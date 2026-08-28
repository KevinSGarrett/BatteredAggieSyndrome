from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = "configs/mounted_acceptance_contract.json"
GATE_RELATIVE = "artifacts/validation/mounted_acceptance_gate.json"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    mutable = {key: value for key, value in gate.items() if key != "gate_identity"}
    return stable_hash(mutable)


def validate_gate_document(gate: Mapping[str, Any], contract: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    if gate.get("schema_version") != "aggie.validation.mounted_acceptance_gate.v1":
        findings.append("MOUNTED_ACCEPTANCE_GATE_SCHEMA_INVALID")
    if gate.get("artifact_type") != "MOUNTED_ACCEPTANCE_GATE":
        findings.append("MOUNTED_ACCEPTANCE_GATE_TYPE_INVALID")
    if gate.get("contract_id") != contract.get("contract_id"):
        findings.append("MOUNTED_ACCEPTANCE_GATE_CONTRACT_MISMATCH")
    if list(gate.get("critical_suite") or []) != list(contract.get("critical_suite") or []):
        findings.append("MOUNTED_ACCEPTANCE_CRITICAL_SUITE_DRIFT")
    if dict(gate.get("skip_budget") or {}) != dict(contract.get("skip_budget") or {}):
        findings.append("MOUNTED_ACCEPTANCE_SKIP_BUDGET_DRIFT")
    if gate.get("network_error_marker") != contract.get("network_error_marker"):
        findings.append("MOUNTED_ACCEPTANCE_NETWORK_MARKER_DRIFT")
    counts = dict(gate.get("counts") or {})
    executed = int(counts.get("executed", 0))
    failures = int(counts.get("failed", 0))
    errors = int(counts.get("errored", 0))
    skipped = int(counts.get("skipped", 0))
    if executed <= 0:
        findings.append("MOUNTED_ACCEPTANCE_ZERO_EXECUTED")
    if failures > 0:
        findings.append("MOUNTED_ACCEPTANCE_FAILURES_PRESENT")
    if errors > 0:
        findings.append("MOUNTED_ACCEPTANCE_ERRORS_PRESENT")
    allowed = int((contract.get("skip_budget") or {}).get("critical_suite_allowed_skips", 0))
    if skipped > allowed:
        findings.append("MOUNTED_ACCEPTANCE_CRITICAL_SKIP_BUDGET_EXCEEDED")
    if gate.get("result") != "PASS":
        findings.append("MOUNTED_ACCEPTANCE_RESULT_NOT_PASS")
    acceptance_result_identity = str(gate.get("acceptance_result_identity") or "")
    if HEX64_RE.fullmatch(acceptance_result_identity) is None:
        findings.append("MOUNTED_ACCEPTANCE_RESULT_IDENTITY_INVALID")
    gate_identity = str(gate.get("gate_identity") or "")
    if HEX64_RE.fullmatch(gate_identity) is None:
        findings.append("MOUNTED_ACCEPTANCE_GATE_IDENTITY_INVALID")
    elif gate_identity != compute_gate_identity(gate):
        findings.append("MOUNTED_ACCEPTANCE_GATE_IDENTITY_MISMATCH")
    return findings


def validate(root: Path = ROOT) -> list[str]:
    contract_path = root / CONTRACT_RELATIVE
    gate_path = root / GATE_RELATIVE
    if not contract_path.is_file():
        return [f"MOUNTED_ACCEPTANCE_CONTRACT_MISSING:{CONTRACT_RELATIVE}"]
    if not gate_path.is_file():
        return [f"MOUNTED_ACCEPTANCE_GATE_MISSING:{GATE_RELATIVE}"]
    contract = load_json(contract_path)
    gate = load_json(gate_path)
    findings = validate_gate_document(gate, contract)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate committed mounted acceptance gate contract.")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    findings = validate(args.repo_root.resolve())
    if findings:
        print(f"FAIL: mounted acceptance gate ({len(findings)} finding(s))")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("PASS: mounted acceptance gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

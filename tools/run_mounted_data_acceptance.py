from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validate_mounted_acceptance_gate import compute_gate_identity  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = "configs/mounted_acceptance_contract.json"
GATE_RELATIVE = "artifacts/validation/mounted_acceptance_gate.json"
EXTERNAL_RESULT_ROOT = "validation/mounted_acceptance/sha256"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX40_RE = re.compile(r"[0-9a-f]{40}")
MATERIALIZATION_AUTHORITY = "PRECOMMITTED_MATERIALIZATION_COMMIT_NOT_SAMPLED_FROM_CHECKOUT"


class AcceptanceFailure(RuntimeError):
    """Raised when mounted acceptance prerequisites or policy checks fail."""


@dataclass(frozen=True)
class RawRequirement:
    source_gate: str
    raw_relative_path: str
    raw_sha256: str


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def resolve_data_root(explicit: str | None) -> Path:
    candidate = explicit or os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "")
    if not candidate.strip():
        raise AcceptanceFailure("AGGIE_ANALYTICS_DATA_ROOT_REQUIRED")
    data_root = Path(candidate).resolve()
    if not data_root.is_dir():
        raise AcceptanceFailure(f"AGGIE_ANALYTICS_DATA_ROOT_MISSING:{data_root}")
    return data_root


def materialization_commit(repo_root: Path, contract: Mapping[str, Any]) -> str:
    """Return the precommitted commit that materialized the mounted acceptance gate.

    This is read from the contract rather than sampled from the working checkout. Every
    other field of the gate is derived from committed content and the mounted data root,
    so sampling HEAD here would make the acceptance result and gate identities a function
    of whichever commit happens to be checked out, and re-materialization after any later
    commit would rewrite the tracked gate for no verified provenance gain.
    """
    value = contract.get("materialization_commit")
    if not isinstance(value, str) or not HEX40_RE.fullmatch(value):
        raise AcceptanceFailure(
            "contract must predeclare materialization_commit as a 40-character lowercase hex commit SHA"
        )
    if contract.get("materialization_commit_authority") != MATERIALIZATION_AUTHORITY:
        raise AcceptanceFailure("materialization_commit authority label missing or altered")
    completed = subprocess.run(
        ["git", "cat-file", "-t", value],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0 or completed.stdout.strip() != "commit":
        raise AcceptanceFailure(f"MATERIALIZATION_COMMIT_NOT_IN_HISTORY:{value}")
    return value


def compute_code_identity(repo_root: Path) -> str:
    members = (
        "tools/run_mounted_data_acceptance.py",
        "tools/validate_mounted_acceptance_gate.py",
        CONTRACT_RELATIVE,
    )
    digest = hashlib.sha256()
    digest.update(b"aggie.validation.mounted_acceptance.code_bundle.v1\n")
    for relative in members:
        path = repo_root / relative
        if not path.is_file():
            raise AcceptanceFailure(f"CODE_BUNDLE_MEMBER_MISSING:{relative}")
        digest.update(relative.replace("\\", "/").encode("utf-8"))
        digest.update(b"\n")
        digest.update(path.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def _iter_tests(suite: unittest.TestSuite) -> Iterable[unittest.case.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_tests(item)
            continue
        yield item


def _collect_capture_rows(gate_relative: str, gate: Mapping[str, Any]) -> list[RawRequirement]:
    rows: list[RawRequirement] = []
    capture = gate.get("capture")
    captures = gate.get("captures")
    if isinstance(capture, Mapping):
        captures = [capture]
    if not isinstance(captures, list):
        return rows
    for row in captures:
        if not isinstance(row, Mapping):
            continue
        raw_relative_path = str(row.get("raw_relative_path") or "")
        raw_sha256 = str(row.get("raw_sha256") or "")
        if not raw_relative_path or HEX64_RE.fullmatch(raw_sha256) is None:
            raise AcceptanceFailure(f"INVALID_RAW_ENTRY:{gate_relative}")
        rows.append(
            RawRequirement(
                source_gate=gate_relative,
                raw_relative_path=raw_relative_path,
                raw_sha256=raw_sha256,
            )
        )
    return rows


def collect_required_raw_manifest(repo_root: Path, contract: Mapping[str, Any]) -> list[RawRequirement]:
    manifest: dict[str, RawRequirement] = {}
    for gate_relative in list(contract.get("required_gates") or []):
        gate_path = repo_root / str(gate_relative)
        if not gate_path.is_file():
            raise AcceptanceFailure(f"REQUIRED_GATE_MISSING:{gate_relative}")
        gate = load_json(gate_path)
        for requirement in _collect_capture_rows(str(gate_relative), gate):
            current = manifest.get(requirement.raw_relative_path)
            if current and current.raw_sha256 != requirement.raw_sha256:
                raise AcceptanceFailure(f"RAW_SHA_CONFLICT:{requirement.raw_relative_path}")
            manifest[requirement.raw_relative_path] = requirement
    return [manifest[path] for path in sorted(manifest)]


def verify_required_raw_manifest(data_root: Path, required: list[RawRequirement]) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for item in required:
        raw_path = data_root / item.raw_relative_path
        if not raw_path.is_file():
            raise AcceptanceFailure(f"REQUIRED_RAW_MISSING:{item.raw_relative_path}")
        actual_sha = sha256_file(raw_path)
        if actual_sha != item.raw_sha256:
            raise AcceptanceFailure(
                f"REQUIRED_RAW_SHA_MISMATCH:{item.raw_relative_path}:expected={item.raw_sha256}:actual={actual_sha}"
            )
        verified.append(
            {
                "source_gate": item.source_gate,
                "raw_relative_path": item.raw_relative_path,
                "raw_sha256": item.raw_sha256,
            }
        )
    return verified


def hydrate_capture_indexes(repo_root: Path, data_root: Path, contract: Mapping[str, Any]) -> None:
    for row in list(contract.get("capture_index_hydration") or []):
        if not isinstance(row, Mapping):
            raise AcceptanceFailure("CAPTURE_INDEX_HYDRATION_ENTRY_INVALID")
        gate_relative = str(row.get("gate_relative") or "")
        capture_index_relative = str(row.get("capture_index_relative") or "")
        if not gate_relative or not capture_index_relative:
            raise AcceptanceFailure("CAPTURE_INDEX_HYDRATION_ENTRY_INCOMPLETE")
        gate = load_json(repo_root / gate_relative)
        captures = list(gate.get("captures") or [])
        if not captures:
            gate_name = Path(gate_relative).name
            if not gate_name.endswith("_gate.json"):
                raise AcceptanceFailure(f"CAPTURE_INDEX_SOURCE_EMPTY:{gate_relative}")
            contract_name = gate_name.replace("_gate.json", "_contract.json")
            contract_path = repo_root / "configs" / contract_name
            if not contract_path.is_file():
                raise AcceptanceFailure(f"CAPTURE_INDEX_CONTRACT_MISSING:{contract_name}")
            upstream_contract = load_json(contract_path)
            normalized_root = str((upstream_contract.get("payloads") or {}).get("normalized_root") or "")
            dataset_identity = str(gate.get("dataset_identity") or "")
            if not normalized_root or HEX64_RE.fullmatch(dataset_identity) is None:
                raise AcceptanceFailure(f"CAPTURE_INDEX_GATE_DATASET_IDENTITY_MISSING:{gate_relative}")
            payload_path = data_root / normalized_root / dataset_identity / "payload.json"
            if not payload_path.is_file():
                raise AcceptanceFailure(f"CAPTURE_INDEX_PAYLOAD_MISSING:{payload_path}")
            payload = load_json(payload_path)
            captures = list(payload.get("captures") or [])
        if not captures:
            raise AcceptanceFailure(f"CAPTURE_INDEX_SOURCE_EMPTY:{gate_relative}")
        hydrated: list[dict[str, Any]] = []
        for index, capture in enumerate(captures, start=1):
            hydrated_row = dict(capture)
            hydrated_row["source_order"] = int(hydrated_row.get("source_order") or index)
            if not hydrated_row.get("url"):
                raise AcceptanceFailure(f"CAPTURE_INDEX_URL_MISSING:{gate_relative}")
            if not hydrated_row.get("raw_relative_path") or not hydrated_row.get("raw_sha256"):
                raise AcceptanceFailure(f"CAPTURE_INDEX_RAW_METADATA_MISSING:{gate_relative}")
            hydrated.append(hydrated_row)
        index_payload = {
            "schema_version": str(gate.get("schema_version") or "aggie.data.capture_index.v1"),
            "captures": sorted(hydrated, key=lambda item: int(item["source_order"])),
        }
        write_json(data_root / capture_index_relative, index_payload)


class CountingResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):  # type: ignore[no-untyped-def]
        super().__init__(stream, descriptions, verbosity)
        self.successes: list[str] = []

    def addSuccess(self, test):  # type: ignore[no-untyped-def]
        super().addSuccess(test)
        self.successes.append(test.id())


def run_critical_suite(repo_root: Path, data_root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    os.environ["AGGIE_ANALYTICS_DATA_ROOT"] = str(data_root)
    os.environ[str(contract.get("network_forbidden_env") or "AGGIE_ANALYTICS_NETWORK_FORBIDDEN")] = "1"
    os.environ[str(contract.get("reconstruct_only_env") or "AGGIE_ANALYTICS_RECONSTRUCT_FROM_LAKE_ONLY")] = "1"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    tests_root = repo_root / "tests"
    if not tests_root.is_dir():
        raise AcceptanceFailure("TESTS_DIRECTORY_MISSING")
    for pattern in list(contract.get("critical_suite") or []):
        suite.addTests(loader.discover(start_dir=str(tests_root), pattern=str(pattern)))
    inventory = [test.id() for test in _iter_tests(suite)]
    runner = unittest.TextTestRunner(verbosity=2, resultclass=CountingResult)
    result = runner.run(suite)
    return {
        "inventory": sorted(inventory),
        "executed": int(result.testsRun),
        "passed": len(result.successes),
        "failed": len(result.failures),
        "errored": len(result.errors),
        "skipped": len(result.skipped),
        "failures": sorted(test.id() for test, _trace in result.failures),
        "errors": sorted(test.id() for test, _trace in result.errors),
        "skips": sorted({"test": test.id(), "reason": reason} for test, reason in result.skipped),
    }


def evaluate_run_policy(run_result: Mapping[str, Any], contract: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    executed = int(run_result.get("executed", 0))
    if executed <= 0:
        findings.append("ZERO_EXECUTED_TESTS")
    allowed_skips = int((contract.get("skip_budget") or {}).get("critical_suite_allowed_skips", 0))
    skipped = int(run_result.get("skipped", 0))
    if skipped > allowed_skips:
        findings.append(f"CRITICAL_SKIP_BUDGET_EXCEEDED:{skipped}>{allowed_skips}")
    if int(run_result.get("failed", 0)) > 0:
        findings.append("TEST_FAILURES_PRESENT")
    if int(run_result.get("errored", 0)) > 0:
        findings.append("TEST_ERRORS_PRESENT")
    return findings


def build_gate(
    *,
    repo_root: Path,
    contract: Mapping[str, Any],
    run_result: Mapping[str, Any],
    raw_manifest: list[dict[str, Any]],
    data_root_manifest_identities: Mapping[str, str],
    acceptance_result_identity: str,
    acceptance_result_relative_path: str,
) -> dict[str, Any]:
    counts = {
        "executed": int(run_result["executed"]),
        "passed": int(run_result["passed"]),
        "failed": int(run_result["failed"]),
        "errored": int(run_result["errored"]),
        "skipped": int(run_result["skipped"]),
    }
    gate: dict[str, Any] = {
        "schema_version": "aggie.validation.mounted_acceptance_gate.v1",
        "artifact_type": "MOUNTED_ACCEPTANCE_GATE",
        "classification": "CYCLE18_19_CRITICAL_MOUNTED_ACCEPTANCE",
        "result": "PASS" if not evaluate_run_policy(run_result, contract) else "FAIL",
        "contract_id": contract["contract_id"],
        "repo_head_sha": materialization_commit(repo_root, contract),
        "repo_head_sha_authority": MATERIALIZATION_AUTHORITY,
        "code_identity": compute_code_identity(repo_root),
        "critical_suite": list(contract.get("critical_suite") or []),
        "test_inventory": list(run_result["inventory"]),
        "test_inventory_identity": stable_hash(list(run_result["inventory"])),
        "skip_budget": dict(contract.get("skip_budget") or {}),
        "expected_full_suite_skips": list(contract.get("expected_full_suite_skips") or []),
        "network_error_marker": str(contract.get("network_error_marker") or ""),
        "counts": counts,
        "failure_tests": list(run_result.get("failures") or []),
        "error_tests": list(run_result.get("errors") or []),
        "skipped_tests": list(run_result.get("skips") or []),
        "required_raw_manifest": raw_manifest,
        "required_raw_manifest_identity": stable_hash(raw_manifest),
        "data_root_manifest_identities": dict(data_root_manifest_identities),
        "acceptance_result_identity": acceptance_result_identity,
        "acceptance_result_relative_path": acceptance_result_relative_path.replace("\\", "/"),
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return gate


def run(repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    required = collect_required_raw_manifest(repo_root, contract)
    verified_raw_manifest = verify_required_raw_manifest(data_root, required)
    hydrate_capture_indexes(repo_root, data_root, contract)
    data_root_manifest_identities: dict[str, str] = {}
    for relative in list(contract.get("data_root_manifests") or []):
        manifest_path = data_root / str(relative)
        if not manifest_path.is_file():
            raise AcceptanceFailure(f"DATA_ROOT_MANIFEST_MISSING:{relative}")
        data_root_manifest_identities[str(relative)] = sha256_file(manifest_path)
    run_result = run_critical_suite(repo_root, data_root, contract)
    findings = evaluate_run_policy(run_result, contract)
    acceptance_result = {
        "schema_version": "aggie.validation.mounted_acceptance_result.v1",
        "contract_id": contract["contract_id"],
        "repo_head_sha": materialization_commit(repo_root, contract),
        "repo_head_sha_authority": MATERIALIZATION_AUTHORITY,
        "code_identity": compute_code_identity(repo_root),
        "critical_suite": list(contract.get("critical_suite") or []),
        "run": run_result,
        "policy_findings": findings,
        "required_raw_manifest_identity": stable_hash(verified_raw_manifest),
        "data_root_manifest_identities": data_root_manifest_identities,
    }
    acceptance_result_identity = stable_hash(acceptance_result)
    acceptance_relative = f"{EXTERNAL_RESULT_ROOT}/{acceptance_result_identity}/acceptance_result.json"
    write_json(data_root / acceptance_relative, acceptance_result)
    gate = build_gate(
        repo_root=repo_root,
        contract=contract,
        run_result=run_result,
        raw_manifest=verified_raw_manifest,
        data_root_manifest_identities=data_root_manifest_identities,
        acceptance_result_identity=acceptance_result_identity,
        acceptance_result_relative_path=acceptance_relative,
    )
    write_json(repo_root / GATE_RELATIVE, gate)
    return {"gate": gate, "acceptance_result": acceptance_result, "findings": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic mounted-data acceptance critical suite.")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--data-root", type=str, default="")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    try:
        data_root = resolve_data_root(args.data_root or None)
        outcome = run(repo_root, data_root)
    except AcceptanceFailure as exc:
        print(f"FAIL: mounted acceptance preflight: {exc}")
        return 1
    findings = list(outcome["findings"])
    gate = dict(outcome["gate"])
    counts = dict(gate.get("counts") or {})
    print(
        "mounted acceptance counts: "
        f"executed={counts.get('executed', 0)} "
        f"passed={counts.get('passed', 0)} "
        f"failed={counts.get('failed', 0)} "
        f"errored={counts.get('errored', 0)} "
        f"skipped={counts.get('skipped', 0)}"
    )
    if findings:
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"PASS: mounted acceptance gate={gate['gate_identity']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

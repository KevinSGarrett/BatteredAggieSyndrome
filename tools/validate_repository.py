from __future__ import annotations

import argparse
import csv
import json
import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.repo_integrity import (
    INTRINSIC_VCS_METADATA,
    scan_forbidden,
    scan_secrets,
    validate_manifest,
    validate_required_structure,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the canonical Aggie Analytics Engine repository.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    findings = []
    findings += validate_required_structure(root)
    findings += scan_forbidden(root)
    findings += scan_secrets(root)
    findings += validate_manifest(root)


    architecture_registry = root / "configs/architecture_registry.json"
    if architecture_registry.exists():
        from tools.validate_architecture import validate_registry
        architecture_findings = validate_registry(json.loads(architecture_registry.read_text(encoding="utf-8")))
        for detail in architecture_findings:
            findings.append(type("F", (), {"kind":"architecture", "path":str(architecture_registry.relative_to(root)), "detail":detail})())

    entity_registry = root / "configs/entity_registry.json"
    if entity_registry.exists():
        from tools.validate_entities import validate as validate_entities
        for detail in validate_entities(root):
            findings.append(type("F", (), {"kind":"entity_contract", "path":str(entity_registry.relative_to(root)), "detail":detail})())

    temporal_registry = root / "configs/temporal_registry.json"
    if temporal_registry.exists():
        from tools.validate_temporal import validate as validate_temporal
        for detail in validate_temporal(root):
            findings.append(type("F", (), {"kind":"temporal_contract", "path":str(temporal_registry.relative_to(root)), "detail":detail})())

    feature_registry = root / "configs/raw_feature_registry.json"
    if feature_registry.exists():
        from tools.validate_feature_registry import validate as validate_feature_registry
        for detail in validate_feature_registry(root):
            findings.append(type("F", (), {"kind":"feature_registry", "path":str(feature_registry.relative_to(root)), "detail":detail})())

    feature_lifecycle_registry = root / "configs/feature_lifecycle_registry.json"
    if feature_lifecycle_registry.exists():
        from tools.validate_feature_lifecycle import validate as validate_feature_lifecycle
        for detail in validate_feature_lifecycle(root):
            findings.append(type("F", (), {"kind":"feature_lifecycle", "path":str(feature_lifecycle_registry.relative_to(root)), "detail":detail})())

    team_state_registry = root / "configs/team_state_registry.json"
    if team_state_registry.exists():
        from tools.validate_team_state import validate as validate_team_state
        for detail in validate_team_state(root):
            findings.append(type("F", (), {"kind":"team_state", "path":str(team_state_registry.relative_to(root)), "detail":detail})())

    acceptance_registry = root / "configs/acceptance_registry.json"
    if acceptance_registry.exists():
        from tools.validate_acceptance import validate as validate_acceptance
        for detail in validate_acceptance(root):
            findings.append(type("F", (), {"kind":"acceptance", "path":str(acceptance_registry.relative_to(root)), "detail":detail})())

    model_architecture_registry = root / "configs/model_architecture_registry.json"
    if model_architecture_registry.exists():
        from tools.validate_model_architecture import validate as validate_model_architecture
        for detail in validate_model_architecture(root):
            findings.append(type("F", (), {"kind":"model_architecture", "path":str(model_architecture_registry.relative_to(root)), "detail":detail})())

    external_storage_policy = root / "configs/external_storage_policy.json"
    if external_storage_policy.exists():
        from tools.validate_external_storage_policy import validate as validate_external_storage_policy
        for detail in validate_external_storage_policy(root):
            findings.append(type("F", (), {"kind":"external_storage", "path":str(external_storage_policy.relative_to(root)), "detail":detail})())

    openai_assist_policy = root / "configs/openai_assist_policy.json"
    if openai_assist_policy.exists():
        from tools.validate_openai_assist import validate as validate_openai_assist
        for detail in validate_openai_assist(root):
            findings.append(type("F", (), {"kind":"openai_assist", "path":str(openai_assist_policy.relative_to(root)), "detail":detail})())

    # Lightweight governance integrity checks.
    req_path = root / "governance/REQUIREMENTS_INDEX.csv"
    trace_path = root / "governance/REQUIREMENTS_TRACEABILITY.csv"
    adr_path = root / "governance/ADR_INDEX.csv"
    risk_path = root / "governance/RISK_REGISTER.csv"
    def ids(path: Path, column: str) -> list[str]:
        with path.open(newline="", encoding="utf-8") as fh:
            return [row[column] for row in csv.DictReader(fh)]
    req_ids = ids(req_path, "requirement_id")
    trace_ids = ids(trace_path, "requirement_id")
    adr_ids = ids(adr_path, "adr_id")
    risk_ids = ids(risk_path, "risk_id")
    if len(req_ids) != len(set(req_ids)):
        findings.append(type("F", (), {"kind":"duplicate_req", "path":str(req_path), "detail":"duplicate requirement IDs"})())
    if set(req_ids) != set(trace_ids):
        findings.append(type("F", (), {"kind":"traceability", "path":str(trace_path), "detail":"traceability does not cover exactly all requirements"})())
    if len(adr_ids) != len(set(adr_ids)):
        findings.append(type("F", (), {"kind":"duplicate_adr", "path":str(adr_path), "detail":"duplicate ADR IDs"})())
    if len(risk_ids) != len(set(risk_ids)):
        findings.append(type("F", (), {"kind":"duplicate_risk", "path":str(risk_path), "detail":"duplicate risk IDs"})())
    # Open-issue references are human-facing but must remain unique to avoid ambiguous carry-forward.
    issue_path = root / "governance/OPEN_ISSUES.md"
    if issue_path.exists():
        issue_ids = re.findall(r"ISSUE-(\d+)", issue_path.read_text(encoding="utf-8"))
        duplicates = sorted({x for x in issue_ids if issue_ids.count(x) > 1})
        if duplicates:
            findings.append(type("F", (), {"kind":"duplicate_issue", "path":str(issue_path), "detail":f"duplicate issue IDs {duplicates}"})())

    # Check explicit numeric requirement/ADR references across text files.
    known_req = set(req_ids)
    known_adr = set(adr_ids)
    text_suffixes = {".md", ".txt", ".csv", ".yaml", ".yml", ".json", ".toml", ".py", ".ps1"}
    for path in root.rglob("*"):
        if any(part in INTRINSIC_VCS_METADATA for part in path.relative_to(root).parts):
            continue
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for ref in set(re.findall(r"REQ-\d{3}", text)) - known_req:
            findings.append(type("F", (), {"kind":"dangling_req_ref", "path":str(path.relative_to(root)), "detail":ref})())
        for ref in set(re.findall(r"ADR-\d{3}", text)) - known_adr:
            findings.append(type("F", (), {"kind":"dangling_adr_ref", "path":str(path.relative_to(root)), "detail":ref})())

    if findings:
        print(f"FAIL: {len(findings)} finding(s)")
        for finding in findings:
            print(f"- {finding.kind}: {finding.path}: {finding.detail}")
        return 1
    print("PASS: repository structure, manifests, governance IDs, secret scan and forbidden-artifact scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

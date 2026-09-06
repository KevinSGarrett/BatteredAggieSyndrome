"""Replacement validator proving Fort Knox/assistive plane has no active authority.

This module must not import retired assistive runtime implementations. It proves
absence of active required-reading, CI, strict-validation, routing, scheduler,
and completion dependencies.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Iterable

RETIRED_READING_MARKERS = (
    "instructions/25_FORT_KNOX_ASSISTIVE_EXECUTION_INTERLOCK.md",
    "validate_codex_usage_interlock.py",
)
ACTIVE_CONTROL_SURFACES = (
    "AGENTS.md",
    "instructions/START_HERE.md",
    ".github/workflows/ci.yml",
    "tools/validate_repository.py",
)
RETIRED_IMPORT_PREFIXES = (
    "aggie_analytics.openai_assist",
    "aggie_analytics.assistive_plane",
)
HISTORICAL_ONLY_LABEL = "RETIRED_HISTORICAL_ONLY"


class DecommissionError(ValueError):
    """Raised when a retired assistive dependency remains active."""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _iter_python(root: Path) -> Iterable[Path]:
    for path in (root / "src").rglob("*.py"):
        yield path
    for path in (root / "tools").glob("*.py"):
        yield path


def agents_requires_fort_knox(root: Path) -> bool:
    text = _read(root / "AGENTS.md")
    return "25_FORT_KNOX_ASSISTIVE_EXECUTION_INTERLOCK.md" in text and (
        "Before any material work, read" in text
    )


def start_here_requires_fort_knox(root: Path) -> bool:
    text = _read(root / "instructions/START_HERE.md")
    return "always, before every material work unit" in text.lower() and (
        "25_FORT_KNOX" in text
    )


def ci_runs_old_interlock(root: Path) -> bool:
    text = _read(root / ".github/workflows/ci.yml")
    return (
        "validate_codex_usage_interlock.py" in text
        or "validate_unified_assistive_plane.py" in text
    )


def repository_strict_calls_old_interlock(root: Path) -> bool:
    text = _read(root / "tools/validate_repository.py")
    return (
        "validate_codex_usage_interlock" in text
        or "validate_unified_assistive_plane" in text
    )


def instruction_manifest_always_reads_fort_knox(root: Path) -> bool:
    manifest = json.loads(
        (root / "instructions/manifest.json").read_text(encoding="utf-8")
    )
    for entry in manifest.get("files", []):
        if entry.get("path") != "instructions/25_FORT_KNOX_ASSISTIVE_EXECUTION_INTERLOCK.md":
            continue
        if entry.get("read_tier") == "ALWAYS":
            return True
        if entry.get("authority") == "P0_ACTIVE_EXECUTION_INTERLOCK":
            return True
    return False


def scientific_modules_import_retired_runtime(root: Path) -> list[str]:
    findings: list[str] = []
    banned_roots = (
        root / "src" / "aggie_analytics" / "cycle28",
        root / "src" / "aggie_analytics" / "scientific_reference",
        root / "src" / "aggie_analytics" / "data",
        root / "src" / "aggie_analytics" / "modeling",
    )
    for base in banned_roots:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            relative = path.relative_to(root).as_posix()
            if "openai_assist" in relative or "assistive_plane" in relative:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith(RETIRED_IMPORT_PREFIXES):
                        findings.append(f"{relative}:{node.module}")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith(RETIRED_IMPORT_PREFIXES):
                            findings.append(f"{relative}:{alias.name}")
    return findings


def definition_of_done_requires_assistive_proof(root: Path) -> bool:
    payload = json.loads(
        (root / "instructions/policies/definition_of_done.json").read_text(encoding="utf-8")
    )
    for check in payload.get("core_checks", []):
        text = str(check.get("requirement") or "")
        if "assistive plane is not independently proven operational" in text:
            return True
        if "direct Codex PROJECT_WORK is absent" in text:
            return True
    return False


def validate_retired_assistive_decommission(root: Path) -> list[str]:
    findings: list[str] = []
    if agents_requires_fort_knox(root):
        findings.append("AGENTS_MD_REQUIRES_FORT_KNOX")
    if start_here_requires_fort_knox(root):
        findings.append("START_HERE_ALWAYS_READS_FORT_KNOX")
    if ci_runs_old_interlock(root):
        findings.append("CI_RUNS_RETIRED_INTERLOCK")
    if repository_strict_calls_old_interlock(root):
        findings.append("STRICT_REPO_VALIDATION_CALLS_RETIRED_INTERLOCK")
    if instruction_manifest_always_reads_fort_knox(root):
        findings.append("INSTRUCTION_MANIFEST_ALWAYS_READS_FORT_KNOX")
    if definition_of_done_requires_assistive_proof(root):
        findings.append("DEFINITION_OF_DONE_REQUIRES_ASSISTIVE_PROOF")
    findings.extend(
        f"SCIENTIFIC_IMPORT_RETIRED:{item}"
        for item in scientific_modules_import_retired_runtime(root)
    )
    ci_text = _read(root / ".github/workflows/ci.yml")
    if "Assistive routing interlock" in ci_text:
        findings.append("CI_JOB_LABEL_ASSISTIVE_ROUTING_INTERLOCK")
    return findings


def validate(root: Path) -> list[str]:
    return validate_retired_assistive_decommission(root)

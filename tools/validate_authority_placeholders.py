"""Reject placeholder ownership identities in authority-bearing project files.

Authority-bearing contracts, gates, and evidence artifacts must name a real Jira
owner. A placeholder such as ``BAT-XXX`` silently detaches an artifact from its
decision unit, so it is rejected everywhere except the explicitly enumerated
stale fixtures that exist to prove the rejection itself.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SCANNED_DIRECTORIES = (
    "configs",
    "governance",
    "artifacts",
    "instructions",
    "jira",
    "docs",
    "provenance",
)

SCANNED_SUFFIXES = {".json", ".csv", ".yaml", ".yml", ".md", ".txt", ".sha256"}

# Keys whose value names the owning decision unit or contract identity.
AUTHORITY_KEYS = (
    "jira_key",
    "jira_identity",
    "contract_id",
    "owner_jira_key",
    "work_unit_id",
    "decision_unit",
    "material_merge_sha",
)

PLACEHOLDER_PATTERN = re.compile(
    r"""(?x)
    BAT-X{2,}            # BAT-XXX and longer runs
    | BAT-(?:TBD|NNN|000)  # other historical stand-ins
    | \{\{\s*JIRA_KEY_PLACEHOLDER\s*\}\}
    """
)

# Fixtures that intentionally retain a placeholder so tests can prove rejection.
ALLOWED_PLACEHOLDER_PATHS = frozenset(
    {
        "tests/fixtures/stale_placeholder_contract.json",
    }
)

# Immutable captured history. These record what a source or board looked like at
# capture time, so they must never be rewritten to satisfy a present-day contract.
EXCLUDED_PREFIXES = ("jira/snapshots/",)

# Sentinels that truthfully record "no owner yet" rather than faking one.
UNSET_OWNER_SENTINELS = frozenset({"", "PENDING_LIVE_SYNCHRONIZATION"})


def _relative_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in SCANNED_DIRECTORIES:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in SCANNED_SUFFIXES:
                paths.append(path)
    return paths


def _iter_authority_values(node: Any, trail: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            where = f"{trail}.{key}" if trail else str(key)
            if key in AUTHORITY_KEYS and isinstance(value, str):
                found.append((where, value))
            found.extend(_iter_authority_values(value, where))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_iter_authority_values(value, f"{trail}[{index}]"))
    return found


def validate(root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    for path in _relative_paths(root):
        relative = path.relative_to(root).as_posix()
        if relative in ALLOWED_PLACEHOLDER_PATHS:
            continue
        if relative.startswith(EXCLUDED_PREFIXES):
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue

        match = PLACEHOLDER_PATTERN.search(text)
        if match is not None:
            findings.append(f"AUTHORITY_PLACEHOLDER_PRESENT:{relative}:{match.group(0)}")

        if path.suffix.lower() != ".json":
            continue
        try:
            document = json.loads(text)
        except json.JSONDecodeError:
            continue
        for where, value in _iter_authority_values(document):
            if PLACEHOLDER_PATTERN.search(value):
                findings.append(f"AUTHORITY_KEY_PLACEHOLDER:{relative}:{where}={value}")
            elif (
                where.endswith("jira_key")
                and value not in UNSET_OWNER_SENTINELS
                and not re.fullmatch(r"BAT-\d+", value)
            ):
                findings.append(f"AUTHORITY_JIRA_KEY_MALFORMED:{relative}:{where}={value}")
    return sorted(set(findings))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reject placeholder ownership identities in authority-bearing files."
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    findings = validate(args.repo_root.resolve())
    if findings:
        print(f"FAIL: authority placeholders ({len(findings)} finding(s))")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("PASS: no placeholder ownership identities in authority-bearing files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

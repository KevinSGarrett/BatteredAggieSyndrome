"""Repository-strict purity fingerprinting for validators and test runs.

A validator or test that rewrites a tracked artifact destroys the evidence it claims to
check: the second run agrees with the first because the first moved the target. Three
season-index suites did exactly that, which hid two stale committed gates on main for an
entire cycle.

This module fingerprints every tracked file, runs a command, then fingerprints again and
reports the exact paths that moved. It also carries the line-ending contract, hashing
canonical LF bytes so a checkout with CRLF endings is not mistaken for a content change,
while still rejecting files whose committed bytes mix endings.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

LINE_ENDING_BASELINE_RELATIVE = "configs/tracked_line_ending_baseline.json"

TEXT_SUFFIXES = frozenset(
    {
        ".csv",
        ".json",
        ".jsonl",
        ".md",
        ".py",
        ".sha256",
        ".txt",
        ".yaml",
        ".yml",
    }
)

MUTATION = "TRACKED_FILE_MUTATED_BY_READ_ONLY_COMMAND"
DELETION = "TRACKED_FILE_DELETED_BY_READ_ONLY_COMMAND"
CREATION = "UNTRACKED_FILE_CREATED_IN_TRACKED_TREE"
MIXED_ENDINGS = "TRACKED_TEXT_FILE_MIXES_LINE_ENDINGS"
BASELINE_STALE = "LINE_ENDING_BASELINE_ENTRY_NO_LONGER_MIXED"


class PurityViolation(RuntimeError):
    """Raised when a command that must be read-only changed the tracked tree."""


@dataclass(frozen=True)
class PurityReport:
    command: tuple[str, ...]
    exit_code: int
    tracked_file_count: int
    mutated: tuple[str, ...] = field(default=())
    deleted: tuple[str, ...] = field(default=())
    created: tuple[str, ...] = field(default=())

    @property
    def pure(self) -> bool:
        return not (self.mutated or self.deleted or self.created)

    def findings(self) -> list[str]:
        return [
            *(f"{MUTATION}:{path}" for path in self.mutated),
            *(f"{DELETION}:{path}" for path in self.deleted),
            *(f"{CREATION}:{path}" for path in self.created),
        ]

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact_type": "TRACKED_FILE_PURITY_REPORT",
            "command": list(self.command),
            "created": list(self.created),
            "deleted": list(self.deleted),
            "exit_code": self.exit_code,
            "findings": self.findings(),
            "mutated": list(self.mutated),
            "result": "PASS" if self.pure else "FAIL",
            "tracked_file_count": self.tracked_file_count,
        }


def tracked_paths(repo_root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    return sorted(
        entry.decode("utf-8") for entry in completed.stdout.split(b"\0") if entry
    )


def canonical_digest(path: Path) -> str:
    """Hash a file, normalizing CRLF to LF for text so checkout style is not a change."""

    body = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        body = body.replace(b"\r\n", b"\n")
    return hashlib.sha256(body).hexdigest()


def fingerprint(repo_root: Path, paths: list[str] | None = None) -> dict[str, str]:
    relatives = paths if paths is not None else tracked_paths(repo_root)
    prints: dict[str, str] = {}
    for relative in relatives:
        path = repo_root / relative
        if path.is_file():
            prints[relative] = canonical_digest(path)
    return prints


def mixed_line_ending_paths(repo_root: Path, paths: list[str] | None = None) -> list[str]:
    """Return tracked text files whose own committed bytes mix CRLF and bare LF."""

    mixed: list[str] = []
    for relative in paths if paths is not None else tracked_paths(repo_root):
        path = repo_root / relative
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        body = path.read_bytes()
        if b"\r\n" in body and body.replace(b"\r\n", b"").count(b"\n"):
            mixed.append(relative)
    return sorted(mixed)


def read_line_ending_baseline(repo_root: Path) -> frozenset[str]:
    """Load the disclosed set of pre-existing mixed-ending files.

    The baseline exists because several offenders belong to pinned code bundles whose
    validator_code_identity is referenced by downstream gates; rewriting them would move
    identities that have nothing to do with line endings. Recording them keeps the
    condition visible and lets new violations fail closed.
    """

    path = repo_root / LINE_ENDING_BASELINE_RELATIVE
    if not path.is_file():
        return frozenset()
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return frozenset(payload.get("mixed_line_ending_paths") or ())


def line_ending_findings(repo_root: Path, paths: list[str] | None = None) -> list[str]:
    """Reject newly mixed endings, and report a baseline entry that has been fixed."""

    baseline = read_line_ending_baseline(repo_root)
    observed = set(mixed_line_ending_paths(repo_root, paths))
    findings = [f"{MIXED_ENDINGS}:{path}" for path in sorted(observed - baseline)]
    findings += [
        f"{BASELINE_STALE}:{path}" for path in sorted(baseline - observed)
    ]
    return findings


def run_and_compare(
    command: list[str],
    *,
    repo_root: Path,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> PurityReport:
    """Run a command that must not touch the tracked tree, and report what moved."""

    relatives = tracked_paths(repo_root)
    before = fingerprint(repo_root, relatives)
    completed = subprocess.run(
        command,
        cwd=cwd or repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    after = fingerprint(repo_root, tracked_paths(repo_root))

    mutated = tuple(
        sorted(path for path, digest in before.items() if after.get(path, digest) != digest)
    )
    deleted = tuple(sorted(set(before) - set(after)))
    created = tuple(sorted(set(after) - set(before)))
    return PurityReport(
        command=tuple(command),
        exit_code=completed.returncode,
        tracked_file_count=len(before),
        mutated=mutated,
        deleted=deleted,
        created=created,
    )


def assert_pure(report: PurityReport) -> None:
    if not report.pure:
        raise PurityViolation("; ".join(report.findings()))

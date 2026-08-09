from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

MANIFEST_NAME = "provenance/PROJECT_FILE_MANIFEST.csv"
HASHES_NAME = "provenance/PROJECT_FILE_HASHES.sha256"
TREE_NAME = "provenance/CURRENT_TREE.txt"


@dataclass(frozen=True)
class Finding:
    kind: str
    path: str
    detail: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_policy(repo_root: Path) -> dict:
    return json.loads((repo_root / "configs/repository_policy.json").read_text(encoding="utf-8"))


def iter_repo_files(repo_root: Path) -> list[Path]:
    return sorted((p for p in repo_root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(repo_root).as_posix())


def posix_rel(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def validate_safe_archive_member(name: str) -> bool:
    if "\\" in name:
        return False
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts:
        return False
    if re.match(r"^[A-Za-z]:", name):
        return False
    return True


def scan_forbidden(repo_root: Path, policy: dict | None = None) -> list[Finding]:
    policy = policy or load_policy(repo_root)
    forbidden_dirs = set(policy["forbidden_directory_names"])
    forbidden_files = set(policy["forbidden_exact_files"])
    forbidden_exts = set(policy["forbidden_extensions"])
    max_bytes = int(policy["max_repository_file_bytes"])
    findings: list[Finding] = []

    for path in repo_root.rglob("*"):
        rel = posix_rel(repo_root, path)
        if any(part in forbidden_dirs for part in path.relative_to(repo_root).parts):
            findings.append(Finding("forbidden_directory", rel, "forbidden directory component"))
            continue
        if path.is_file():
            if path.name in forbidden_files:
                findings.append(Finding("forbidden_file", rel, "forbidden exact filename"))
            if path.suffix.lower() in forbidden_exts:
                findings.append(Finding("forbidden_extension", rel, path.suffix.lower()))
            if path.stat().st_size > max_bytes:
                findings.append(Finding("oversized_file", rel, str(path.stat().st_size)))
    return findings


def scan_secrets(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    known_patterns = [
        ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
        ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
        ("openai_style_key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
        ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ]
    generic_assignment = re.compile(
        r"(?i)(?:api[_-]?key|token|secret|password)\s*[:=]\s*[\"']?([A-Za-z0-9_./+=-]{16,})"
    )
    text_exts = {".py", ".ps1", ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".env", ".example", ".csv"}
    placeholders = ("OPTIONAL_LOCAL_SECRET", "LOCAL_PATH_OUTSIDE_REPOSITORY", "CHANGEME", "PLACEHOLDER", "YOUR_")

    for path in iter_repo_files(repo_root):
        if path.suffix.lower() not in text_exts and path.name not in {".env.example", ".gitignore", ".gitattributes", ".editorconfig"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = posix_rel(repo_root, path)
        for kind, pattern in known_patterns:
            if pattern.search(text):
                findings.append(Finding(kind, rel, "known credential pattern"))
        if rel != ".env.example":
            for m in generic_assignment.finditer(text):
                value = m.group(1)
                if not any(x in value.upper() for x in placeholders):
                    findings.append(Finding("generic_secret_assignment", rel, "credential-like assignment"))
    return findings


def generate_current_tree(repo_root: Path) -> None:
    tree_path = repo_root / TREE_NAME
    rels = [posix_rel(repo_root, p) for p in iter_repo_files(repo_root) if posix_rel(repo_root, p) != TREE_NAME]
    tree_path.parent.mkdir(parents=True, exist_ok=True)
    tree_path.write_text("\n".join(rels) + "\n", encoding="utf-8", newline="\n")


def manifest_rows(repo_root: Path, policy: dict | None = None) -> list[dict[str, str | int]]:
    policy = policy or load_policy(repo_root)
    excluded = set(policy["manifest_exclude"])
    rows = []
    for path in iter_repo_files(repo_root):
        rel = posix_rel(repo_root, path)
        if rel in excluded:
            continue
        rows.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return rows


def tree_fingerprint(rows: Iterable[dict[str, str | int]]) -> str:
    h = hashlib.sha256()
    for row in sorted(rows, key=lambda r: str(r["path"])):
        h.update(f'{row["sha256"]}  {row["path"]}\n'.encode("utf-8"))
    return h.hexdigest()


def write_manifest(repo_root: Path) -> tuple[list[dict[str, str | int]], str]:
    generate_current_tree(repo_root)
    rows = manifest_rows(repo_root)
    manifest_path = repo_root / MANIFEST_NAME
    hash_path = repo_root / HASHES_NAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    hash_path.write_text(
        "".join(f'{row["sha256"]}  {row["path"]}\n' for row in sorted(rows, key=lambda r: str(r["path"]))),
        encoding="utf-8",
        newline="\n",
    )
    return rows, tree_fingerprint(rows)


def validate_manifest(repo_root: Path) -> list[Finding]:
    manifest_path = repo_root / MANIFEST_NAME
    if not manifest_path.exists():
        return [Finding("manifest_missing", MANIFEST_NAME, "manifest does not exist")]
    with manifest_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    findings: list[Finding] = []
    seen: set[str] = set()
    for row in rows:
        rel = row["path"]
        if rel in seen:
            findings.append(Finding("manifest_duplicate", rel, "duplicate path"))
        seen.add(rel)
        path = repo_root / Path(*PurePosixPath(rel).parts)
        if not path.exists():
            findings.append(Finding("manifest_missing_file", rel, "listed file absent"))
            continue
        actual_size = path.stat().st_size
        if actual_size != int(row["bytes"]):
            findings.append(Finding("manifest_size", rel, f'{actual_size} != {row["bytes"]}'))
        actual_hash = sha256_file(path)
        if actual_hash != row["sha256"]:
            findings.append(Finding("manifest_hash", rel, f'{actual_hash} != {row["sha256"]}'))
    policy = load_policy(repo_root)
    expected = {posix_rel(repo_root, p) for p in iter_repo_files(repo_root)} - set(policy["manifest_exclude"])
    missing_from_manifest = expected - seen
    extra = seen - expected
    findings.extend(Finding("manifest_coverage", p, "file not represented") for p in sorted(missing_from_manifest))
    findings.extend(Finding("manifest_extra", p, "manifest path not in expected set") for p in sorted(extra))
    return findings


def validate_required_structure(repo_root: Path, policy: dict | None = None) -> list[Finding]:
    policy = policy or load_policy(repo_root)
    findings: list[Finding] = []
    for rel in policy["required_root_files"]:
        if not (repo_root / rel).is_file():
            findings.append(Finding("required_file_missing", rel, "required root file"))
    for rel in policy["required_root_directories"]:
        if not (repo_root / rel).is_dir():
            findings.append(Finding("required_directory_missing", rel, "required root directory"))
    return findings

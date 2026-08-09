from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable

sys.dont_write_bytecode = True

_HASH_RE = re.compile(r"[0-9a-f]{64}")
_PIN_RE = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)"
    r"(?:\s*;\s*(.+))?$"
)
_ALLOWED_MARKERS = {None, 'platform_system == "Windows"'}


def normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


@dataclass(frozen=True)
class LockEntry:
    name: str
    version: str
    marker: str | None
    hashes: tuple[str, ...]

    @property
    def normalized_name(self) -> str:
        return normalize_name(self.name)


def _logical_lines(text: str) -> list[str]:
    logical: list[str] = []
    parts: list[str] = []
    for line_number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            if parts:
                raise ValueError(f"line {line_number}: continuation interrupted")
            continue
        continuation = stripped.endswith("\\")
        token = stripped[:-1].strip() if continuation else stripped
        if not token:
            raise ValueError(f"line {line_number}: empty continuation token")
        parts.append(token)
        if not continuation:
            logical.append(" ".join(parts))
            parts = []
    if parts:
        raise ValueError("unterminated line continuation")
    return logical


def parse_lock_text(text: str) -> list[LockEntry]:
    entries: list[LockEntry] = []
    seen: set[str] = set()
    for line_number, logical in enumerate(_logical_lines(text), 1):
        pieces = re.split(r"\s+--hash=sha256:", logical)
        if len(pieces) < 2:
            raise ValueError(f"entry {line_number}: missing --hash=sha256 directive")
        head = pieces[0].strip()
        match = _PIN_RE.fullmatch(head)
        if not match:
            raise ValueError(f"entry {line_number}: requirement is not one exact pin")
        name, version, marker = match.groups()
        marker = marker.strip() if marker else None
        if marker not in _ALLOWED_MARKERS:
            raise ValueError(f"entry {line_number}: unsupported environment marker {marker!r}")
        hashes = tuple(piece.strip() for piece in pieces[1:])
        if any(not _HASH_RE.fullmatch(value) for value in hashes):
            raise ValueError(f"entry {line_number}: malformed SHA-256 directive")
        if len(set(hashes)) != len(hashes):
            raise ValueError(f"entry {line_number}: duplicate SHA-256 directive")
        normalized = normalize_name(name)
        if normalized in seen:
            raise ValueError(f"entry {line_number}: duplicate package {normalized}")
        seen.add(normalized)
        entries.append(LockEntry(name=name, version=version, marker=marker, hashes=hashes))
    if not entries:
        raise ValueError("lock contains no package entries")
    return entries


def parse_lock(path: Path) -> list[LockEntry]:
    return parse_lock_text(path.read_text(encoding="utf-8"))


def marker_applies(marker: str | None, platform_system: str | None = None) -> bool:
    if marker is None:
        return True
    if marker == 'platform_system == "Windows"':
        return (platform_system or platform.system()) == "Windows"
    raise ValueError(f"unsupported environment marker {marker!r}")


def lock_policy_errors(path: Path) -> tuple[list[LockEntry], list[str]]:
    try:
        entries = parse_lock(path)
    except (OSError, UnicodeError, ValueError) as exc:
        return [], [str(exc)]
    return entries, []


def _license_metadata_kind(metadata: Any) -> str:
    if str(metadata.get("License-Expression") or "").strip():
        return "SPDX_EXPRESSION"
    legacy = str(metadata.get("License") or "").strip()
    if legacy and legacy.upper() not in {"UNKNOWN", "NONE"}:
        return "LEGACY_LICENSE"
    classifiers = metadata.get_all("Classifier") or []
    if any(str(value).startswith("License ::") for value in classifiers):
        return "CLASSIFIER"
    return "MISSING"


def _license_files(files: Iterable[Any]) -> list[str]:
    found: list[str] = []
    for item in files:
        value = str(item).replace("\\", "/")
        name = PurePosixPath(value).name.upper()
        if name.startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE")):
            found.append(value)
    return sorted(set(found))


def build_installed_inventory(
    entries: list[LockEntry],
    *,
    distribution_getter: Callable[[str], Any] = importlib.metadata.distribution,
    platform_system: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    packages: list[dict[str, Any]] = []
    errors: list[str] = []
    for entry in sorted(entries, key=lambda item: item.normalized_name):
        if not marker_applies(entry.marker, platform_system):
            continue
        try:
            distribution = distribution_getter(entry.name)
        except importlib.metadata.PackageNotFoundError:
            errors.append(f"missing installed distribution: {entry.name}=={entry.version}")
            continue
        actual_version = str(distribution.version)
        metadata_kind = _license_metadata_kind(distribution.metadata)
        license_files = _license_files(distribution.files or [])
        if actual_version != entry.version:
            errors.append(
                f"installed version mismatch for {entry.name}: {actual_version} != {entry.version}"
            )
        if metadata_kind == "MISSING":
            errors.append(f"missing license metadata for {entry.name}=={entry.version}")
        if not license_files:
            errors.append(f"missing installed license/notice file for {entry.name}=={entry.version}")
        packages.append(
            {
                "name": entry.normalized_name,
                "version": actual_version,
                "license_metadata_kind": metadata_kind,
                "license_or_notice_files": license_files,
            }
        )
    return packages, errors


def build_report(lock_path: Path, *, check_installed: bool) -> dict[str, Any]:
    lock_bytes = lock_path.read_bytes()
    entries, errors = lock_policy_errors(lock_path)
    packages: list[dict[str, Any]] = []
    if check_installed and not errors:
        packages, installed_errors = build_installed_inventory(entries)
        errors.extend(installed_errors)
    return {
        "schema_version": "1.0.0",
        "report_type": "product_supply_chain_machine_inventory",
        "result": "PASS" if not errors else "FAIL",
        "lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        "locked_package_count": len(entries),
        "installed_package_count_checked": len(packages),
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "cryptographic_hash_enforcement": not errors or bool(entries),
        "legal_approval_claimed": False,
        "human_rights_review_required": True,
        "packages": packages,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--check-installed", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    lock_path = (args.lock or root / "requirements" / "product.lock").resolve()
    report = build_report(lock_path, check_installed=args.check_installed)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    if report["result"] == "PASS":
        print(
            "PASS: product supply-chain policy "
            f"({report['locked_package_count']} hash-locked packages; "
            f"{report['installed_package_count_checked']} installed inventories checked)"
        )
        return 0
    print("FAIL: product supply-chain policy")
    for error in report["errors"]:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

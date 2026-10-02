r"""Detect content-addressed lake payloads that were damaged in place.

TP37-S. A canonical payload was found destroyed on 2026-09-22:

    features/tamu_official_historical_coverage_inventory/sha256/
        d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37/
        inventory.json

The identity directory kept its original 2026-08-19 creation time while the
file inside it was rewritten to zero bytes 34 days later. Nothing noticed.
``tools/validate_repository.py --strict`` does exercise that payload, but only
when the private lake is actually mounted, and CI never mounts it -- so the
repository was green while its own strict validator could not run to
completion locally.

The checks here are invariants, not heuristics, so an empty file that is
genuinely empty is not reported:

``in_place_rewrite`` (WARNING -- a risk, not proof of damage)
    A content-addressed payload is immutable by construction: its directory
    name *is* the identity of its contents. A file whose *modification* time
    is meaningfully later than its own *creation* time was rewritten after it
    was written, which cannot be legitimate for an immutable payload.

    Comparing against the creation time of the file -- not of the directory --
    is what separates the two things that look alike here. Sidecars added to
    an identity directory long afterwards (``*.bat581_bind.json`` and
    friends) are created late but never rewritten, so they are reported
    separately as ``late_sidecar`` and are not corruption. Only a file that
    existed and then changed is.

    Creation time is available on Windows (``st_ctime``) and on platforms
    exposing ``st_birthtime``. Where neither exists -- ordinary Linux -- the
    check reports itself unavailable instead of guessing, and the JSON checks
    below still run.

    A rewrite whose new bytes are identical does no harm, so this is reported
    as a WARNING and does not by itself fail the scan. It matters because it
    is the *mechanism* of the one confirmed loss: a truncating rewrite of an
    immutable payload that ran out of disk. 200 payloads here were rewritten
    in place after being written.

``unparsable_json`` (CRITICAL -- demonstrable corruption)
    A ``.json`` payload that does not parse is corrupt regardless of size.

``empty_json`` (CRITICAL -- demonstrable corruption)
    JSON has no empty document. A zero-byte ``.json`` file is corrupt. A
    zero-byte ``.jsonl`` file is NOT reported: zero rows is a valid record
    set, and twelve such files here were written atomically alongside their
    non-empty siblings.

Read-only. This tool never repairs, deletes or rewrites anything: restoring a
canonical payload is an operator decision with its own authority.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterator


class _bas_atomic:  # U37-11: atomic writes once this tool has imported the package itself
    @staticmethod
    def _module():
        import sys as _bas_sys

        if "aggie_analytics" not in _bas_sys.modules:
            return None  # never bind the package from another tree before the tool does
        try:
            from aggie_analytics import atomic_io
        except ImportError:
            return None
        return atomic_io

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_text(path, *args, **kwargs) if module else path.write_text(*args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_bytes(path, *args, **kwargs) if module else path.write_bytes(*args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        module = cls._module()
        return module.open_write(path, *args, **kwargs) if module else path.open(*args, **kwargs)


sys.dont_write_bytecode = True

IDENTITY = re.compile(r"^[0-9a-f]{64}$")

#: Filesystem timestamps are coarse and a copy can shift them slightly. Only a
#: rewrite well after the directory was created is reported.
REWRITE_TOLERANCE_SECONDS = 120.0

DEFAULT_SUBTREES = ("features", "canonical")


def creation_time(stat: os.stat_result) -> float | None:
    """Creation time where the platform actually reports one.

    ``st_birthtime`` on the platforms that have it, ``st_ctime`` on Windows
    where it is creation. On Linux ``st_ctime`` is the inode-change time,
    which a rewrite also updates, so it would make every rewritten file look
    untouched -- there, ``None`` is returned and the caller says so.
    """

    birthtime = getattr(stat, "st_birthtime", None)
    if birthtime is not None:
        return float(birthtime)
    if os.name == "nt":
        return float(stat.st_ctime)
    return None


def identity_directories(root: Path, subtrees: tuple[str, ...]) -> Iterator[Path]:
    for subtree in subtrees:
        base = root / subtree
        if not base.is_dir():
            continue
        for dataset in sorted(base.iterdir()):
            sha_root = dataset / "sha256"
            if not sha_root.is_dir():
                continue
            for identity in sorted(sha_root.iterdir()):
                if identity.is_dir() and IDENTITY.match(identity.name):
                    yield identity


def inspect_identity(identity: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    try:
        directory_stat = identity.stat()
    except OSError as error:
        return [
            {
                "kind": "unreadable_identity",
                "path": str(identity),
                "detail": str(error),
            }
        ]

    identity_fixed_at = min(directory_stat.st_ctime, directory_stat.st_mtime)

    for payload in sorted(identity.rglob("*")):
        if not payload.is_file():
            continue
        try:
            stat = payload.stat()
        except OSError as error:
            findings.append(
                {"kind": "unreadable_payload", "path": str(payload), "detail": str(error)}
            )
            continue

        created_at = creation_time(stat)
        if created_at is None:
            findings.append(
                {
                    "kind": "rewrite_check_unavailable",
                    "path": str(payload),
                    "detail": (
                        "this platform exposes no file creation time, so an "
                        "in-place rewrite cannot be distinguished from a late "
                        "sidecar here"
                    ),
                    "severity": "INFO",
                }
            )
        elif stat.st_mtime > created_at + REWRITE_TOLERANCE_SECONDS:
            findings.append(
                {
                    "kind": "in_place_rewrite",
                    "path": str(payload),
                    "detail": (
                        "payload was modified long after it was created; a "
                        "content-addressed payload is immutable once written"
                    ),
                    "identity_fixed_at_epoch": identity_fixed_at,
                    "payload_created_at_epoch": created_at,
                    "payload_modified_at_epoch": stat.st_mtime,
                    "size_bytes": stat.st_size,
                    "severity": "WARNING",
                }
            )
        elif created_at > identity_fixed_at + REWRITE_TOLERANCE_SECONDS:
            findings.append(
                {
                    "kind": "late_sidecar",
                    "path": str(payload),
                    "detail": (
                        "file was added to an existing identity directory "
                        "after the identity was fixed; it was never rewritten"
                    ),
                    "identity_fixed_at_epoch": identity_fixed_at,
                    "payload_created_at_epoch": created_at,
                    "severity": "INFO",
                }
            )

        if payload.suffix == ".json":
            if stat.st_size == 0:
                findings.append(
                    {
                        "kind": "empty_json",
                        "path": str(payload),
                        "detail": "JSON has no empty document; this payload is truncated",
                        "size_bytes": 0,
                        "severity": "CRITICAL",
                    }
                )
                continue
            try:
                json.loads(payload.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                findings.append(
                    {
                        "kind": "unparsable_json",
                        "path": str(payload),
                        "detail": str(error),
                        "size_bytes": stat.st_size,
                        "severity": "CRITICAL",
                    }
                )
    return findings


def scan(root: Path, subtrees: tuple[str, ...]) -> dict[str, Any]:
    if not root.is_dir():
        # An absent lake is reported as absent. It is NOT reported as a pass:
        # substituting "nothing to check" for "checked and clean" is how the
        # hosted runs stayed green while the local lake was broken.
        return {
            "state": "LAKE_NOT_MOUNTED",
            "data_root": str(root),
            "identities_scanned": 0,
            "payloads_scanned": 0,
            "findings": [],
            "finding_count": 0,
        }

    findings: list[dict[str, Any]] = []
    identities = payloads = 0
    for identity in identity_directories(root, subtrees):
        identities += 1
        payloads += sum(1 for p in identity.rglob("*") if p.is_file())
        findings.extend(inspect_identity(identity))

    critical = [f for f in findings if f.get("severity") == "CRITICAL"]
    warnings = [f for f in findings if f.get("severity") == "WARNING"]
    if critical:
        state = "DAMAGED_PAYLOADS_FOUND"
    elif warnings:
        state = "MUTABLE_PAYLOAD_RISK"
    else:
        state = "CLEAN"
    return {
        "state": state,
        "critical_count": len(critical),
        "warning_count": len(warnings),
        "data_root": str(root),
        "subtrees": list(subtrees),
        "identities_scanned": identities,
        "payloads_scanned": payloads,
        "findings": findings,
        "finding_count": len(findings),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Lake root. Defaults to the resolved workspace data root.",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--subtree",
        action="append",
        default=None,
        help="Lake subtree to scan; repeatable. Defaults to features and canonical.",
    )
    parser.add_argument(
        "--require-mounted",
        action="store_true",
        help="Exit non-zero when the lake is not mounted instead of reporting it.",
    )
    args = parser.parse_args(argv)

    root = args.data_root
    if root is None:
        repo_root = Path(__file__).resolve().parents[1]
        if str(repo_root / "src") not in sys.path:
            sys.path.insert(0, str(repo_root / "src"))
        from aggie_analytics.workspace.paths import resolve_layout

        root = resolve_layout().root("data")

    report = scan(Path(root), tuple(args.subtree or DEFAULT_SUBTREES))
    body = json.dumps(report, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        _bas_atomic.write_text(args.output, body + "\n", encoding="utf-8")
    print(body if report["finding_count"] <= 25 else json.dumps(
        {k: v for k, v in report.items() if k != "findings"}
        | {"findings_truncated": report["findings"][:25]},
        indent=2,
        sort_keys=True,
    ))

    if report["state"] == "LAKE_NOT_MOUNTED":
        return 1 if args.require_mounted else 0
    return 1 if report.get("critical_count") else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

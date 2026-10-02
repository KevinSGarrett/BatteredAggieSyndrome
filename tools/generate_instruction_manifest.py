from __future__ import annotations

"""Regenerate or check non-circular instruction hashes without inventing metadata."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

sys.dont_write_bytecode = True


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def generate(repo_root: Path, *, check: bool = False) -> list[str]:
    root = repo_root.resolve() / "instructions"
    manifest_path = root / "manifest.json"
    ledger_path = root / "FILE_HASHES.sha256"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = {"instructions/" + p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}
    listed = {entry["path"]: entry for entry in manifest["files"]}
    errors: list[str] = []
    if set(actual) != set(listed):
        errors.extend(f"unlisted:{p}" for p in sorted(set(actual) - set(listed)))
        errors.extend(f"missing:{p}" for p in sorted(set(listed) - set(actual)))
        return errors
    for rel, entry in listed.items():
        desired = None if rel.endswith(("/manifest.json", "/FILE_HASHES.sha256")) else _sha(actual[rel])
        if check and entry.get("sha256") != desired:
            errors.append(f"manifest_hash:{rel}")
        entry["sha256"] = desired
    encoded = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if not check:
        temporary = manifest_path.with_suffix(".json.tmp")
        _bas_atomic.write_text(temporary, encoded, encoding="utf-8", newline="\n")
        os.replace(temporary, manifest_path)
    ledger_lines = []
    for path in sorted((p for p in root.rglob("*") if p.is_file() and p.name != "FILE_HASHES.sha256"), key=lambda p: p.relative_to(root).as_posix()):
        ledger_lines.append(f"{_sha(path)}  {path.relative_to(root).as_posix()}\n")
    desired_ledger = "".join(ledger_lines)
    if check:
        if ledger_path.read_text(encoding="utf-8") != desired_ledger:
            errors.append("hash_ledger_stale")
    else:
        temporary = ledger_path.with_suffix(".sha256.tmp")
        _bas_atomic.write_text(temporary, desired_ledger, encoding="utf-8", newline="\n")
        os.replace(temporary, ledger_path)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors = generate(args.repo_root, check=args.check)
    print(json.dumps({"result": "PASS" if not errors else "FAIL", "check": args.check, "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

"""Build a deterministic, secret-safe full repository transfer ZIP from a validated stage."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.packaging import deterministic_zip_tree, safe_extract, safe_zip_names
from tools.repo_integrity import scan_forbidden, scan_secrets, validate_manifest, write_manifest

EXCLUDED_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", "env", "node_modules", ".mypy_cache", ".ruff_cache", ".tox", ".idea", ".vscode"}
EXCLUDED_NAMES = {".env", ".DS_Store", "Thumbs.db"}
EXCLUDED_SUFFIXES = {".zip", ".log", ".db", ".sqlite", ".sqlite3", ".joblib", ".pkl", ".pickle", ".pt", ".pth", ".ckpt", ".onnx"}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _included(repo: Path, path: Path) -> bool:
    rel = path.relative_to(repo)
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES or path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return True


def _run(repo: Path, command: list[str]) -> None:
    completed = subprocess.run(command, cwd=repo, text=True, capture_output=True, check=False)
    if completed.returncode:
        summary = (completed.stdout + "\n" + completed.stderr).strip()[-6000:]
        raise RuntimeError(f"Gate failed ({completed.returncode}): {' '.join(command)}\n{summary}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    gates = [
        [sys.executable, "-B", "tools/validate_autonomous_controls.py", "--repo-root", ".", "--strict"],
        [sys.executable, "-B", "tools/validate_jira_control_plane.py", "--repo-root", ".", "--strict"],
        [sys.executable, "-B", "tools/validate_w25_final.py", "--repo-root", "."],
        [sys.executable, "-B", "tools/validate_repository.py", "--repo-root", ".", "--strict"],
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
        [sys.executable, "-B", "-W", "error", "-m", "unittest", "discover", "-s", "tests", "-v"],
    ]
    for command in gates:
        _run(repo, command)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "BatteredAggieSyndrome_with_Autonomous_Instructions_v2.0.0.zip"
    temporary = output.with_name(output.name + ".tmp")
    with tempfile.TemporaryDirectory(prefix="bas_repo_export_") as td:
        stage = Path(td) / "BatteredAggieSyndrome"
        stage.mkdir()
        files = [path for path in repo.rglob("*") if path.is_file() and _included(repo, path)]
        for source in files:
            target = stage / source.relative_to(repo)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        write_manifest(stage)
        findings = scan_forbidden(stage) + scan_secrets(stage) + validate_manifest(stage)
        if findings:
            sample = [f"{item.kind}:{item.path}:{item.detail}" for item in findings[:50]]
            raise RuntimeError("Staged repository rejected: " + "; ".join(sample))
        deterministic_zip_tree(stage, temporary, root_name="BatteredAggieSyndrome")
        names = safe_zip_names(temporary)
        if len(names) != len(set(names)) or len({name.lower() for name in names}) != len(names):
            raise RuntimeError("ZIP duplicate or case-colliding members")
        with zipfile.ZipFile(temporary) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"ZIP CRC failure: {bad}")
        verify_dir = Path(td) / "verify"
        safe_extract(temporary, verify_dir)
        extracted = verify_dir / "BatteredAggieSyndrome"
        extracted_findings = scan_forbidden(extracted) + scan_secrets(extracted) + validate_manifest(extracted)
        if extracted_findings:
            raise RuntimeError(f"Extracted repository rejected with {len(extracted_findings)} findings")
    os.replace(temporary, output)
    digest = _sha(output)
    sidecar = output.with_suffix(output.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {output.name}\n", encoding="utf-8", newline="\n")
    print(json.dumps({"result": "PASS", "zip": str(output), "sha256": digest, "members": len(names), "sidecar": str(sidecar)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

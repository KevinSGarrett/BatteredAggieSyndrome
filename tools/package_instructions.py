from __future__ import annotations

"""Build and extract-verify the deterministic standalone instruction ZIP."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.packaging import deterministic_zip_tree, safe_extract, safe_zip_names
from tools.validate_autonomous_controls import validate


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    findings = validate(repo, strict=True)
    if findings:
        print(json.dumps({"result": "FAIL", "findings": findings}, indent=2))
        return 1
    manifest = json.loads((repo / "instructions/manifest.json").read_text(encoding="utf-8"))
    version = manifest["instruction_pack_version"]
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"BatteredAggieSyndrome_Autonomous_Instructions_v{version}.zip"
    temporary = output.with_name(output.name + ".tmp")
    if temporary.exists():
        temporary.unlink()
    deterministic_zip_tree(repo / "instructions", temporary, root_name="instructions")
    names = safe_zip_names(temporary)
    expected = {"instructions/" + p.relative_to(repo / "instructions").as_posix() for p in (repo / "instructions").rglob("*") if p.is_file()}
    if len(names) != len(set(names)) or set(names) != expected or len({n.lower() for n in names}) != len(names):
        temporary.unlink(missing_ok=True)
        raise SystemExit("Instruction ZIP member coverage/uniqueness mismatch")
    with zipfile.ZipFile(temporary) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"Instruction ZIP CRC failure: {bad}")
    with tempfile.TemporaryDirectory(prefix="bas_instruction_verify_") as td:
        stage = Path(td)
        safe_extract(temporary, stage)
        extracted = stage / "instructions"
        for path in repo.joinpath("instructions").rglob("*"):
            if path.is_file():
                rel = path.relative_to(repo / "instructions")
                if _sha(path) != _sha(extracted / rel):
                    raise SystemExit(f"Instruction extraction hash mismatch: {rel.as_posix()}")
    os.replace(temporary, output)
    digest = _sha(output)
    sidecar = output.with_suffix(output.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {output.name}\n", encoding="utf-8", newline="\n")
    print(json.dumps({"result": "PASS", "zip": str(output), "sha256": digest, "members": len(names), "sidecar": str(sidecar)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from tools.repo_integrity import (
    HASHES_NAME,
    MANIFEST_NAME,
    load_policy,
    manifest_rows,
    sha256_file,
    tree_fingerprint,
    validate_safe_archive_member,
    write_manifest,
)

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _zip_info(name: str, executable: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    mode = 0o755 if executable else 0o644
    info.external_attr = (mode & 0xFFFF) << 16
    info.create_system = 3
    return info


def deterministic_zip_tree(source_dir: Path, output_zip: Path, root_name: str | None = None) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    root_name = root_name or source_dir.name
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted((p for p in source_dir.rglob("*") if p.is_file()), key=lambda p: p.relative_to(source_dir).as_posix()):
            rel = path.relative_to(source_dir).as_posix()
            arc = f"{root_name}/{rel}" if root_name else rel
            executable = bool(path.stat().st_mode & stat.S_IXUSR) or path.suffix.lower() in {".sh"}
            zf.writestr(_zip_info(arc, executable), path.read_bytes())


def deterministic_zip_flat(source_dir: Path, output_zip: Path) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted((p for p in source_dir.rglob("*") if p.is_file()), key=lambda p: p.relative_to(source_dir).as_posix()):
            rel = path.relative_to(source_dir).as_posix()
            zf.writestr(_zip_info(rel, False), path.read_bytes())


def safe_zip_names(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
    names = [info.filename for info in infos]
    bad = [n for n in names if not validate_safe_archive_member(n)]
    if bad:
        raise ValueError(f"unsafe ZIP paths: {bad[:5]}")
    symlinks = [info.filename for info in infos if ((info.external_attr >> 16) & 0o170000) == stat.S_IFLNK]
    if symlinks:
        raise ValueError(f"ZIP symlink members are not allowed: {symlinks[:5]}")
    return names


def safe_extract(zip_path: Path, dest: Path) -> None:
    safe_zip_names(zip_path)
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            target = (dest / Path(*PurePosixPath(member.filename).parts)).resolve()
            if root != target and root not in target.parents:
                raise ValueError(f"unsafe extraction target: {member.filename}")
        zf.extractall(dest)


def _simple_yaml_scalar(path: Path, key: str) -> str:
    prefix = f"{key}:"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            value = line.split(":", 1)[1].strip()
            return value.strip("'\"")
    raise KeyError(f"{key} not found in {path}")


def _normalized_project_id(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def build_cumulative(repo_root: Path, output_zip: Path) -> tuple[str, int, str]:
    rows, fingerprint = write_manifest(repo_root)
    deterministic_zip_tree(repo_root, output_zip, root_name=repo_root.name)
    return sha256_file(output_zip), sum(1 for p in repo_root.rglob("*") if p.is_file()), fingerprint


def build_hydration(
    repo_root: Path,
    cumulative_zip: Path,
    hydration_zip: Path,
    previous_cumulative_sha256: str | None,
    generation_timestamp_utc: str,
) -> dict:
    config = json.loads((repo_root / "configs/hydration_manifest.json").read_text(encoding="utf-8"))
    project_id = _simple_yaml_scalar(repo_root / "governance/PROJECT_IDENTITY.yaml", "project_id")
    project_version = _simple_yaml_scalar(repo_root / "governance/PROJECT_IDENTITY.yaml", "project_version")
    current_wave = _simple_yaml_scalar(repo_root / "governance/PROJECT_IDENTITY.yaml", "current_wave")
    next_wave = _simple_yaml_scalar(repo_root / "governance/PROJECT_IDENTITY.yaml", "next_wave")
    governance_version = _simple_yaml_scalar(repo_root / "governance/PROJECT_IDENTITY.yaml", "governance_version")
    wave_status = _simple_yaml_scalar(repo_root / "governance/PROJECT_IDENTITY.yaml", "wave_status")
    recon_edition = _simple_yaml_scalar(repo_root / "governance/PROJECT_IDENTITY.yaml", "reconnaissance_edition")
    wave_plan_revision = _simple_yaml_scalar(repo_root / "governance/PROJECT_IDENTITY.yaml", "wave_plan_revision")
    wave_number = int(current_wave[1:])
    rows = manifest_rows(repo_root)
    cumulative_sha = sha256_file(cumulative_zip)
    binding = {
        "project_id": "AGGIE_ANALYTICS_ENGINE",
        "project_name": "Aggie Analytics Engine",
        "wave_number": wave_number,
        "wave": current_wave,
        "parent_wave": f"W{wave_number-1:02d}" if wave_number > 1 else None,
        "project_version": project_version,
        "cumulative_zip_filename": cumulative_zip.name,
        "cumulative_zip_sha256": cumulative_sha,
        "previous_cumulative_zip_sha256": previous_cumulative_sha256,
        "repository_file_count": sum(1 for p in repo_root.rglob("*") if p.is_file()),
        "repository_manifest_rows": len(rows),
        "repository_tree_fingerprint": tree_fingerprint(rows),
        "generation_timestamp_utc": generation_timestamp_utc,
        "current_wave_status": wave_status,
        "next_wave": next_wave,
        "major_governance_version": governance_version,
        "reconnaissance_pack_identity": recon_edition,
        "wave_plan_revision_version": wave_plan_revision,
        "manifest_policy": "Repository manifest/hash files exclude themselves; cumulative ZIP SHA is authoritative at pack level.",
        "zip_policy": "sorted members, fixed ZIP timestamps/permissions, safe relative paths"
    }
    with tempfile.TemporaryDirectory(prefix="aggie_hydration_") as td:
        stage = Path(td)
        for item in config["files"]:
            source = repo_root / item["source"]
            if not source.is_file():
                raise FileNotFoundError(f"hydration source missing: {item['source']}")
            target = stage / item["archive"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        (stage / "PACK_BINDING.json").write_text(json.dumps(binding, indent=2) + "\n", encoding="utf-8", newline="\n")
        if current_wave == "W25":
            hydrate_first = f"""# HYDRATE FIRST — Aggie Analytics Engine {current_wave}\n\nThis is the terminal 25-wave recovery pack. It is bound to the exact final cumulative repository below.\n\n## Bound cumulative repository\n- File: `{cumulative_zip.name}`\n- SHA-256: `{cumulative_sha}`\n- Project ID: `AGGIE_ANALYTICS_ENGINE`\n- Final numbered wave: `{current_wave}`\n- Next state: `{next_wave}`\n\n## Mandatory implementation-handoff recovery order\n1. Read this file.\n2. Read and validate `PACK_BINDING.json`.\n3. Compute SHA-256 of the attached cumulative ZIP and require an exact match.\n4. Verify project identity and that the numbered wave program ended at W25.\n5. Safely extract the verified cumulative repository; never rebuild from memory.\n6. Read `AGENTS.md`, `governance/NEXT_WAVE.md`, `docs/final/CODEX_HANDOFF.md`, `docs/final/FINAL_IMPLEMENTATION_PRIORITY.md`, and `docs/final/FIRST_72_HOUR_IMPLEMENTATION_QUEUE.md`.\n7. Preserve all protected PIT/leakage/evaluation/promotion rules while implementing the final backlog.\n8. Do not create Wave 26. Future work is implementation/research backlog execution against this final canonical handoff.\n9. Keep AC-038 / THR-011 / THR-012 unresolved until representative target-hardware evidence exists.\n10. Do not invent model performance, A&M specialization lift, Aggie Excess, BAS effect, or production feature/model selection.\n\n## Critical state\n- National historical foundation + disproportionately deep Texas A&M specialization remains the protected objective.\n- PIT/known-at correctness, no leakage, provenance and empirical promotion remain protected.\n- Recon FINAL v1.2 remains starting evidence, not the full historical data lake.\n"""
        else:
            hydrate_first = f"""# HYDRATE FIRST — Aggie Analytics Engine {current_wave}\n\nThis pack is the compact recovery state for **{current_wave}** and is bound to the exact cumulative repository below.\n\n## Bound cumulative repository\n- File: `{cumulative_zip.name}`\n- SHA-256: `{cumulative_sha}`\n- Project ID: `AGGIE_ANALYTICS_ENGINE`\n- Current completed wave: `{current_wave}`\n- Next allowed wave: `{next_wave}`\n\n## Mandatory recovery order for {next_wave}\n1. Read this file.\n2. Read and validate `PACK_BINDING.json`.\n3. Compute SHA-256 of the attached cumulative ZIP and require an exact match.\n4. Verify project identity/current/next wave.\n5. Use `python tools/verify_prior_wave.py --hydration <HYDRATION.zip> --cumulative <CUMULATIVE.zip> --expected-next-wave {next_wave}` when available.\n6. Safely extract the verified cumulative repository; never rebuild from memory.\n7. Read repository `AGENTS.md`, `governance/NEXT_WAVE.md`, relevant requirements/ADRs, open issues, risks, assumptions and adaptive logs.\n8. Perform the required {next_wave} Adaptive Review before mutation.\n9. Modify the extracted canonical tree cumulatively; never create a disconnected wave tree.\n10. Complete {next_wave} only.\n\n## Critical state\n- National historical foundation + disproportionately deep Texas A&M specialization remains the protected objective.\n- PIT/known-at correctness, no leakage, provenance and empirical promotion remain protected.\n- Read the current architecture/governance artifacts from this hydration pack; do not infer state from an earlier wave's prose.\n- Recon FINAL v1.2 remains starting evidence, not the full historical data lake.\n"""
        (stage / "HYDRATE_FIRST.md").write_text(hydrate_first, encoding="utf-8", newline="\n")
        hash_lines = []
        for p in sorted((p for p in stage.rglob("*") if p.is_file() and p.name != "HYDRATION_FILE_HASHES.sha256"), key=lambda p: p.relative_to(stage).as_posix()):
            hash_lines.append(f"{sha256_file(p)}  {p.relative_to(stage).as_posix()}\n")
        (stage / "HYDRATION_FILE_HASHES.sha256").write_text("".join(hash_lines), encoding="utf-8", newline="\n")
        deterministic_zip_flat(stage, hydration_zip)
    return binding


def _simple_yaml_scalar_text(text: str, key: str) -> str:
    prefix = f"{key}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip().strip("'\"")
    raise KeyError(key)


def verify_prior_pair(hydration_zip: Path, cumulative_zip: Path, expected_next_wave: str | None = None) -> dict:
    safe_zip_names(hydration_zip)
    cumulative_names = safe_zip_names(cumulative_zip)
    with zipfile.ZipFile(hydration_zip) as zf:
        binding = json.loads(zf.read("PACK_BINDING.json"))
        identity_text = zf.read("PROJECT_IDENTITY.yaml").decode("utf-8")
        state_text = zf.read("CURRENT_STATE.yaml").decode("utf-8")
        identity_project = _simple_yaml_scalar_text(identity_text, "project_id")
        identity_wave = _simple_yaml_scalar_text(identity_text, "current_wave")
        identity_next = _simple_yaml_scalar_text(identity_text, "next_wave")
        try:
            state_wave = _simple_yaml_scalar_text(state_text, "current_wave")
        except KeyError:
            # Backward compatibility: W06 emitted the equivalent key as `wave`.
            state_wave = _simple_yaml_scalar_text(state_text, "wave")
        state_next = _simple_yaml_scalar_text(state_text, "next_wave")
        if "HYDRATION_FILE_HASHES.sha256" in zf.namelist():
            for line in zf.read("HYDRATION_FILE_HASHES.sha256").decode("utf-8").splitlines():
                if not line.strip():
                    continue
                expected_hash, name = line.split("  ", 1)
                actual_hash = hashlib.sha256(zf.read(name)).hexdigest()
                if actual_hash != expected_hash:
                    raise ValueError(f"hydration file hash mismatch: {name}")
    if _normalized_project_id(identity_project) != _normalized_project_id(binding["project_id"]):
        raise ValueError("hydration project identity mismatch")
    if identity_wave != binding["wave"] or state_wave != binding["wave"]:
        raise ValueError("hydration current-wave mismatch")
    if identity_next != binding["next_wave"] or state_next != binding["next_wave"]:
        raise ValueError("hydration next-wave mismatch")
    expected_root = "Aggie_Analytics_Engine/"
    if not cumulative_names or any(not n.startswith(expected_root) for n in cumulative_names):
        raise ValueError("cumulative ZIP does not contain the expected canonical root")
    actual = sha256_file(cumulative_zip)
    if actual != binding["cumulative_zip_sha256"]:
        raise ValueError(f"cumulative SHA mismatch: {actual} != {binding['cumulative_zip_sha256']}")
    if expected_next_wave and binding["next_wave"] != expected_next_wave:
        raise ValueError(f"next-wave mismatch: {binding['next_wave']} != {expected_next_wave}")
    return binding

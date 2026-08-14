from __future__ import annotations

"""Validate the autonomous instruction/control system as an executable contract."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

sys.dont_write_bytecode = True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path, findings: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        findings.append(f"invalid_json:{path.as_posix()}:{type(exc).__name__}")
        return {}
    if not isinstance(value, dict):
        findings.append(f"invalid_json_root:{path.as_posix()}")
        return {}
    return value


def _safe_rel(value: str) -> bool:
    if "\\" in value or re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def _validate_manifest(repo: Path, findings: list[str]) -> dict[str, Any]:
    root = repo / "instructions"
    manifest = _load_json(root / "manifest.json", findings)
    entries = manifest.get("files", [])
    if not isinstance(entries, list):
        findings.append("manifest:files_not_list")
        return manifest
    actual = {
        "instructions/" + path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    listed: set[str] = set()
    topics: set[str] = set()
    required = {
        "path", "purpose", "authority", "read_tier", "when_to_read",
        "agent_roles", "dependencies", "version", "canonical_topic", "sha256",
    }
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            findings.append(f"manifest:entry_{index}_not_object")
            continue
        missing = required - set(entry)
        if missing:
            findings.append(f"manifest:{index}:missing:{','.join(sorted(missing))}")
            continue
        rel = str(entry["path"])
        if not _safe_rel(rel) or not rel.startswith("instructions/"):
            findings.append(f"manifest:unsafe_path:{rel}")
            continue
        if rel in listed:
            findings.append(f"manifest:duplicate_path:{rel}")
        listed.add(rel)
        topic = str(entry["canonical_topic"])
        if topic in topics:
            findings.append(f"manifest:duplicate_topic:{topic}")
        topics.add(topic)
        for field in ("purpose", "authority", "read_tier", "when_to_read", "version", "canonical_topic"):
            if not str(entry.get(field, "")).strip():
                findings.append(f"manifest:{rel}:blank_{field}")
        if not entry.get("agent_roles"):
            findings.append(f"manifest:{rel}:no_agent_roles")
        target = repo / Path(*PurePosixPath(rel).parts)
        if target.is_file() and entry.get("sha256") is not None:
            actual_hash = _sha256(target)
            if actual_hash != entry["sha256"]:
                findings.append(f"manifest:hash:{rel}:{actual_hash}!={entry['sha256']}")
    for rel in sorted(actual - listed):
        findings.append(f"manifest:unlisted:{rel}")
    for rel in sorted(listed - actual):
        findings.append(f"manifest:missing_file:{rel}")
    if manifest.get("entrypoint") != "instructions/START_HERE.md":
        findings.append("manifest:entrypoint")
    if manifest.get("final_numbered_wave") != "W25" or manifest.get("wave_26_allowed") is not False:
        findings.append("manifest:no_wave_26_boundary")
    return manifest


def _validate_hash_ledger(repo: Path, findings: list[str]) -> None:
    root = repo / "instructions"
    ledger = root / "FILE_HASHES.sha256"
    rows: dict[str, str] = {}
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            findings.append(f"hash_ledger:syntax:{number}")
            continue
        digest, rel = match.groups()
        if rel in rows:
            findings.append(f"hash_ledger:duplicate:{rel}")
        rows[rel] = digest
    expected = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "FILE_HASHES.sha256"
    }
    for rel in sorted(expected - set(rows)):
        findings.append(f"hash_ledger:missing:{rel}")
    for rel in sorted(set(rows) - expected):
        findings.append(f"hash_ledger:extra:{rel}")
    for rel in sorted(expected & set(rows)):
        actual = _sha256(root / Path(*PurePosixPath(rel).parts))
        if actual != rows[rel]:
            findings.append(f"hash_ledger:hash:{rel}:{actual}!={rows[rel]}")


def _validate_links(repo: Path, findings: list[str]) -> None:
    markdown_link = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    for source in sorted((repo / "instructions").rglob("*.md")):
        text = source.read_text(encoding="utf-8")
        for raw in markdown_link.findall(text):
            target = raw.strip().split("#", 1)[0].strip().strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if any(token in target for token in ("<", ">", "{{", "}}")):
                continue
            resolved = (source.parent / target).resolve()
            try:
                resolved.relative_to(repo.resolve())
            except ValueError:
                findings.append(f"link:outside_repo:{source.relative_to(repo).as_posix()}:{target}")
                continue
            if not resolved.exists():
                findings.append(f"link:missing:{source.relative_to(repo).as_posix()}:{target}")


def _validate_policies(repo: Path, findings: list[str]) -> None:
    policy_root = repo / "instructions" / "policies"
    for path in sorted(policy_root.glob("*.json")):
        policy = _load_json(path, findings)
        if path.name.endswith(".schema.json"):
            if not policy.get("$schema") or not policy.get("$id"):
                findings.append(f"policy:json_schema_identity:{path.name}")
        elif policy.get("schema_version") != 2:
            findings.append(f"policy:schema:{path.name}")
        canonical = policy.get("canonical_human_document")
        if canonical and not (repo / Path(*PurePosixPath(str(canonical)).parts)).is_file():
            findings.append(f"policy:canonical_missing:{path.name}:{canonical}")
    prompt = _load_json(policy_root / "prompt_compliance.json", findings)
    entries = prompt.get("entries", [])
    sections = [entry.get("section") for entry in entries if isinstance(entry, dict)]
    if prompt.get("section_count") != 56 or len(entries) != 56 or len(set(sections)) != 56:
        findings.append("compliance:expected_56_unique_sections")
    atomic = _load_json(repo / "instructions/catalogs/master_prompt_atomic_requirements.json", findings)
    requirements = atomic.get("requirements", [])
    if atomic.get("section_count") != 56 or atomic.get("atomic_requirement_count") != len(requirements):
        findings.append("compliance:atomic_counts")
    dod = _load_json(policy_root / "definition_of_done.json", findings)
    if len(dod.get("core_checks", [])) != 16:
        findings.append("policy:dod_core_checks_not_16")
    task_selection = _load_json(policy_root / "task_selection_policy.json", findings)
    if task_selection.get("priority_order") != ["P0", "P1", "P2", "P3"]:
        findings.append("policy:task_priority_order")
    state = _load_json(policy_root / "task_state_machine.json", findings)
    if not state.get("states") or not state.get("transitions") or not state.get("ready_predicates"):
        findings.append("policy:task_state_machine_incomplete")
    permissions = _load_json(policy_root / "autonomy_permissions.json", findings)
    classes = permissions.get("classes", {})
    if not all(name in classes for name in ("AUTO", "AUTO_WITH_GATES", "HUMAN_REQUIRED")):
        findings.append("policy:autonomy_classes")
    git_policy = _load_json(policy_root / "git_policy.json", findings)
    encoded = json.dumps(git_policy, sort_keys=True).lower()
    if "codex/bat-" not in encoded or "force" not in encoded or "main" not in encoded:
        findings.append("policy:git_invariants")


def _validate_catalog(repo: Path, findings: list[str]) -> None:
    catalog = _load_json(repo / "instructions/catalogs/validation_command_catalog.json", findings)
    for group in ("available_validator_tools", "available_test_modules"):
        values = catalog.get(group, [])
        if len(values) != len(set(values)) and group != "available_validator_tools":
            findings.append(f"catalog:duplicates:{group}")
        for rel in sorted(set(values)):
            if not _safe_rel(rel) or not (repo / Path(*PurePosixPath(rel).parts)).is_file():
                findings.append(f"catalog:missing:{rel}")
    command_ids = [item.get("id") for item in catalog.get("global_commands", []) if isinstance(item, dict)]
    if len(command_ids) != len(set(command_ids)) or not {"VAL-AUTO", "VAL-JIRA", "VAL-W25", "VAL-REPO", "VAL-UNIT"}.issubset(command_ids):
        findings.append("catalog:global_commands")


def _validate_root_controls(repo: Path, findings: list[str]) -> None:
    required = [
        "AGENTS.md", ".gitignore", ".gitattributes", ".env.example",
        ".github/pull_request_template.md", ".github/CODEOWNERS",
        "instructions/START_HERE.md", "governance/CURRENT_STATE.yaml",
        "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    ]
    for rel in required:
        if not (repo / Path(*PurePosixPath(rel).parts)).is_file():
            findings.append(f"root_control:missing:{rel}")
    state = (repo / "governance/CURRENT_STATE.yaml").read_text(encoding="utf-8")
    if (
        "current_wave: W25" not in state
        or "wave_program_complete: true" not in state
        or "next_wave: CODEX_IMPLEMENTATION_HANDOFF" not in state
    ):
        findings.append("root_control:no_wave_26_boundary")


def _scan_secrets(repo: Path, findings: list[str]) -> None:
    patterns = {
        "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
        "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    }
    roots = [repo / "instructions", repo / "tools", repo / "tests", repo / ".github"]
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(path for path in root.rglob("*") if path.is_file()):
            if path.suffix.lower() not in {".py", ".ps1", ".md", ".json", ".yaml", ".yml", ".csv", ".txt"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for name, pattern in patterns.items():
                if pattern.search(text):
                    findings.append(f"secret:{name}:{path.relative_to(repo).as_posix()}")


def validate(repo_root: Path, *, strict: bool = False) -> list[str]:
    repo = repo_root.resolve()
    findings: list[str] = []
    _validate_manifest(repo, findings)
    _validate_hash_ledger(repo, findings)
    _validate_links(repo, findings)
    _validate_policies(repo, findings)
    _validate_catalog(repo, findings)
    _validate_root_controls(repo, findings)
    _scan_secrets(repo, findings)
    return sorted(set(findings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    findings = validate(args.repo_root, strict=args.strict)
    result = {"validator": "autonomous_controls", "strict": args.strict, "result": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

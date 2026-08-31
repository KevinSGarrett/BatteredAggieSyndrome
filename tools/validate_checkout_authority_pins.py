from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping

CONTRACT_RELATIVE = Path("configs/authority_checkout_sampling_contract.json")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _canonical_hash(payload: Mapping[str, Any], identity_field: str) -> str:
    material = dict(payload)
    material.pop(identity_field, None)
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.as_posix()} must contain a JSON object")
    return value


def _tokenize(path_expr: str) -> list[str]:
    return [token for token in path_expr.split(".") if token]


def _resolve_matches(payload: Any, path_expr: str) -> list[tuple[str, Any]]:
    nodes: list[tuple[str, Any]] = [("", payload)]
    for token in _tokenize(path_expr):
        token_match = re.fullmatch(r"([^.[]+)(?:\[(\d*)\])?", token)
        if token_match is None:
            return []
        key = token_match.group(1)
        index = token_match.group(2)
        next_nodes: list[tuple[str, Any]] = []
        for prefix, node in nodes:
            if not isinstance(node, Mapping) or key not in node:
                continue
            value = node[key]
            child_prefix = f"{prefix}.{key}" if prefix else key
            if index == "":
                if not isinstance(value, list):
                    continue
                for index, item in enumerate(value):
                    next_nodes.append((f"{child_prefix}[{index}]", item))
            elif index is not None:
                if not isinstance(value, list):
                    continue
                position = int(index)
                if 0 <= position < len(value):
                    next_nodes.append((f"{child_prefix}[{position}]", value[position]))
            else:
                next_nodes.append((child_prefix, value))
        nodes = next_nodes
    return nodes


def _resolve_one(payload: Mapping[str, Any], path_expr: str) -> Any:
    matches = _resolve_matches(payload, path_expr)
    if len(matches) != 1:
        raise ValueError(f"{path_expr} must resolve to exactly one value")
    return matches[0][1]


def _materialize_indexed_path(template: str, resolved_path: str) -> str:
    materialized = template
    indexes = re.findall(r"\[(\d+)\]", resolved_path)
    for index in indexes:
        materialized = materialized.replace("[]", f"[{index}]", 1)
    return materialized


def _iter_key_paths(payload: Any, *, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else key
            yield path, value
            yield from _iter_key_paths(value, prefix=path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            path = f"{prefix}[{index}]"
            yield from _iter_key_paths(value, prefix=path)


def _is_commit_in_history(repo_root: Path, sha: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "cat-file", "-e", f"{sha}^{{commit}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _is_ancestor_of_head(repo_root: Path, sha: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", sha, "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def validate_checkout_authority_pins(
    repo_root: Path, contract: Mapping[str, Any] | None = None
) -> list[str]:
    findings: list[str] = []
    root = repo_root.resolve()
    spec = contract or _load_json(root / CONTRACT_RELATIVE)

    if int(spec.get("schema_version") or 0) != 1:
        findings.append("authority checkout contract schema_version must be 1")

    authority_keys = set(spec.get("authority_key_names") or [])
    if not authority_keys:
        findings.append("authority key list is empty")

    payload_by_path: dict[str, dict[str, Any]] = {}
    declared_by_artifact: dict[str, set[str]] = {}

    for artifact in spec.get("artifacts") or []:
        path = str(artifact.get("path") or "")
        if not path:
            findings.append("artifact path is missing in authority checkout contract")
            continue
        full = root / path
        if not full.is_file():
            findings.append(f"missing scoped authority artifact: {path}")
            continue
        payload = _load_json(full)
        payload_by_path[path] = payload
        declared: set[str] = set()

        identity_field = str(artifact.get("identity_field") or "")
        if identity_field:
            stored = payload.get(identity_field)
            computed = _canonical_hash(payload, identity_field)
            if stored != computed:
                findings.append(
                    f"{path}::{identity_field} outer identity mismatch stored={stored} computed={computed}"
                )

        for rule in artifact.get("rules") or []:
            rule_path = str(rule.get("path") or "")
            role = str(rule.get("role") or "")
            if not rule_path:
                findings.append(f"{path}: rule path is missing")
                continue
            matches = _resolve_matches(payload, rule_path)
            if not matches:
                findings.append(f"{path}::{rule_path} missing declared authority path")
                continue
            declared.update(resolved for resolved, _ in matches)
            for resolved, value in matches:
                if not isinstance(value, str) or not HEX40.fullmatch(value.lower()):
                    findings.append(f"{path}::{resolved} must be a 40-hex commit pin")
                    continue
                sha = value.lower()
                if role == "AUTHORITATIVE_PINNED":
                    if not _is_commit_in_history(root, sha):
                        findings.append(f"{path}::{resolved} pin is absent from git history")
                    if bool(rule.get("must_be_git_ancestor_of_head")) and not _is_ancestor_of_head(
                        root, sha
                    ):
                        findings.append(f"{path}::{resolved} pin is not an ancestor of HEAD")
                    label_expr = str(rule.get("authority_label_path") or "")
                    required_label = str(rule.get("required_authority_label") or "")
                    if label_expr and required_label:
                        candidate = None
                        if "[]" in label_expr:
                            sibling_expr = _materialize_indexed_path(label_expr, resolved)
                            sibling_matches = _resolve_matches(payload, sibling_expr)
                            if len(sibling_matches) == 1:
                                candidate = sibling_matches[0][1]
                        else:
                            try:
                                candidate = _resolve_one(payload, label_expr)
                            except ValueError:
                                candidate = None
                        if candidate != required_label:
                            findings.append(
                                f"{path}::{resolved} missing authority label {required_label}"
                            )
                elif role != "DIAGNOSTIC_NON_AUTHORITY":
                    findings.append(f"{path}::{resolved} has unsupported role {role}")

        declared_by_artifact[path] = declared
        seen_authority_paths = {
            key_path
            for key_path, _ in _iter_key_paths(payload)
            if key_path.rsplit(".", 1)[-1] in authority_keys
        }
        undeclared = sorted(seen_authority_paths - declared)
        for key_path in undeclared:
            findings.append(f"{path}::{key_path} uses undeclared checkout authority key")

    for relation in spec.get("cross_artifact_equalities") or []:
        left = str(relation.get("left") or "")
        right = str(relation.get("right") or "")
        if "::" not in left or "::" not in right:
            findings.append("cross-artifact equality entries must use file::path format")
            continue
        left_file, left_path = left.split("::", 1)
        right_file, right_path = right.split("::", 1)
        left_payload = payload_by_path.get(left_file)
        right_payload = payload_by_path.get(right_file)
        if left_payload is None or right_payload is None:
            continue
        try:
            left_value = _resolve_one(left_payload, left_path)
            right_value = _resolve_one(right_payload, right_path)
        except ValueError as exc:
            findings.append(str(exc))
            continue
        if left_value != right_value:
            findings.append(
                f"cross-artifact checkout pin mismatch: {left_file}::{left_path} != {right_file}::{right_path}"
            )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    findings = validate_checkout_authority_pins(args.repo_root)
    if findings:
        print("FAIL: checkout authority pin findings")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("PASS: checkout authority pins are explicit, declared and history-pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

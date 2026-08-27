from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

CONTRACT_RELATIVE = Path("configs") / "artifact_binding_contract.json"
SHA256_RE = re.compile(r"\b[0-9a-f]{64}\b")
TOKEN_RE = re.compile(r"([^.\[]+)(?:\[([^\[\]]*)\])?")


class ArtifactBindingError(ValueError):
    def __init__(self, message: str, *, path: str | None = None, json_path: str | None = None) -> None:
        self.path = path
        self.json_path = json_path
        location = ""
        if path:
            location += path
        if json_path:
            location += f"::{json_path}"
        prefix = f"{location}: " if location else ""
        super().__init__(f"{prefix}{message}")


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def compute_identity(payload: Mapping[str, Any], identity_field: str) -> str:
    mutable = dict(payload)
    mutable.pop(identity_field, None)
    # Stream the canonical JSON into the digest to avoid peak-memory spikes
    # when strict validators hash large payloads.
    encoder = json.JSONEncoder(
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    digest = hashlib.sha256()
    for chunk in encoder.iterencode(mutable):
        digest.update(chunk.encode("utf-8"))
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract_path = repo_root / CONTRACT_RELATIVE
    if not contract_path.is_file():
        raise ArtifactBindingError(
            "missing artifact-binding contract",
            path=str(CONTRACT_RELATIVE),
        )
    return json.loads(contract_path.read_text(encoding="utf-8"))


def _split_path(path: str) -> list[tuple[str, str | None]]:
    tokens: list[tuple[str, str | None]] = []
    remainder = path
    while remainder:
        if remainder.startswith("."):
            remainder = remainder[1:]
        match = TOKEN_RE.match(remainder)
        if not match:
            raise ArtifactBindingError(f"unparseable JSON path {path!r}", json_path=path)
        tokens.append((match.group(1), match.group(2)))
        remainder = remainder[match.end() :]
    return tokens


def resolve_path(document: Any, path: str) -> list[tuple[str, Any]]:
    nodes: list[tuple[str, Any]] = [("", document)]
    for name, selector in _split_path(path):
        next_nodes: list[tuple[str, Any]] = []
        for current_path, node in nodes:
            if not isinstance(node, Mapping) or name not in node:
                continue
            child = node[name]
            child_path = f"{current_path}.{name}" if current_path else name
            if selector is None:
                next_nodes.append((child_path, child))
                continue
            if not isinstance(child, list):
                continue
            if selector == "":
                for index, item in enumerate(child):
                    next_nodes.append((f"{child_path}[{index}]", item))
                continue
            if selector.isdigit():
                index = int(selector)
                if 0 <= index < len(child):
                    next_nodes.append((f"{child_path}[{index}]", child[index]))
                continue
            if "=" not in selector:
                raise ArtifactBindingError(
                    f"unsupported selector [{selector}]",
                    json_path=path,
                )
            field, expected = selector.split("=", 1)
            for index, item in enumerate(child):
                if isinstance(item, Mapping) and str(item.get(field)) == expected:
                    next_nodes.append((f"{child_path}[{index}]", item))
        nodes = next_nodes
    return nodes


def _require_one(nodes: list[tuple[str, Any]], *, path: str, json_path: str) -> Any:
    if not nodes:
        raise ArtifactBindingError("missing JSON path", path=path, json_path=json_path)
    if len(nodes) != 1:
        raise ArtifactBindingError(
            f"ambiguous JSON path matched {len(nodes)} nodes",
            path=path,
            json_path=json_path,
        )
    return nodes[0][1]


def _collect_values(document: Any, paths: Iterable[str], *, file_path: str) -> list[tuple[str, Any]]:
    collected: list[tuple[str, Any]] = []
    for json_path in paths:
        nodes = resolve_path(document, json_path)
        if not nodes:
            raise ArtifactBindingError("missing JSON path", path=file_path, json_path=json_path)
        collected.extend(nodes)
    return collected


def _as_hash_set(values: Iterable[Any]) -> set[str]:
    hashes: set[str] = set()
    for value in values:
        if isinstance(value, str):
            hashes.update(SHA256_RE.findall(value.lower()))
        elif isinstance(value, list):
            hashes.update(_as_hash_set(value))
    return hashes


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_canonical(repo_root: Path, binding: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    relative = str(binding["canonical_artifact_path"])
    artifact_path = repo_root / relative
    if not artifact_path.is_file():
        raise ArtifactBindingError("missing canonical artifact", path=relative)
    payload = _load_json(artifact_path)
    identity_field = str(binding["identity_field"])
    if binding.get("identity_mode") != "canonical_json_excluding_identity_field":
        raise ArtifactBindingError(
            f"unsupported identity_mode {binding.get('identity_mode')!r}",
            path=str(CONTRACT_RELATIVE),
            json_path=f"bindings[binding_id={binding['binding_id']}].identity_mode",
        )
    computed = compute_identity(payload, identity_field)
    stored = payload.get(identity_field)
    if stored != computed:
        raise ArtifactBindingError(
            f"canonical identity mismatch stored={stored} computed={computed}",
            path=relative,
            json_path=identity_field,
        )
    for field, expected in (binding.get("required_equal") or {}).items():
        actual = payload.get(field)
        if actual != expected:
            raise ArtifactBindingError(
                f"required field {field}={actual!r} expected {expected!r}",
                path=relative,
                json_path=field,
            )
    for json_path in binding.get("forbidden_true_paths") or []:
        for resolved, value in resolve_path(payload, json_path):
            if value is True:
                raise ArtifactBindingError(
                    "forbidden production or protected authority claim is true",
                    path=relative,
                    json_path=resolved,
                )
    lane = payload.get("lane_decision")
    if lane in set(binding.get("forbidden_lane_values") or []):
        raise ArtifactBindingError(
            f"lane decision {lane!r} is not allowed",
            path=relative,
            json_path="lane_decision",
        )
    return payload, computed


def _validate_surface(
    repo_root: Path,
    binding: Mapping[str, Any],
    surface: Mapping[str, Any],
    canonical: Mapping[str, Any],
    current_identity: str,
) -> None:
    relative = str(surface["path"])
    evidence_path = repo_root / relative
    if not evidence_path.is_file():
        raise ArtifactBindingError("missing evidence surface", path=relative)
    document = _load_json(evidence_path)
    expected_jira = surface.get("expected_jira_key") or binding["jira_key"]
    expected_local = surface.get("expected_local_issue_id") or binding["local_issue_id"]
    if surface.get("jira_key_path"):
        actual_jira = _require_one(
            resolve_path(document, str(surface["jira_key_path"])),
            path=relative,
            json_path=str(surface["jira_key_path"]),
        )
        if actual_jira != expected_jira:
            raise ArtifactBindingError(
                f"jira_key mismatch {actual_jira!r} expected {expected_jira!r}",
                path=relative,
                json_path=str(surface["jira_key_path"]),
            )
    if surface.get("local_issue_id_path"):
        actual_local = _require_one(
            resolve_path(document, str(surface["local_issue_id_path"])),
            path=relative,
            json_path=str(surface["local_issue_id_path"]),
        )
        if actual_local != expected_local:
            raise ArtifactBindingError(
                f"local_issue_id mismatch {actual_local!r} expected {expected_local!r}",
                path=relative,
                json_path=str(surface["local_issue_id_path"]),
            )

    # A matching outer evidence hash only proves that the evidence document was
    # rehashed.  The phase bindings declare the semantic fields that must
    # independently agree with their canonical gate, including all counts and
    # authority boundaries that are easy to misstate in a narrative.
    for comparison in surface.get("canonical_to_evidence_paths") or []:
        if not isinstance(comparison, Mapping):
            raise ArtifactBindingError(
                "canonical-to-evidence comparison must be an object",
                path=str(CONTRACT_RELATIVE),
                json_path=f"bindings[binding_id={binding['binding_id']}].canonical_to_evidence_paths",
            )
        canonical_path = str(comparison.get("canonical_path") or "")
        evidence_path_name = str(comparison.get("evidence_path") or "")
        if not canonical_path or not evidence_path_name:
            raise ArtifactBindingError(
                "canonical-to-evidence comparison requires canonical_path and evidence_path",
                path=str(CONTRACT_RELATIVE),
                json_path=f"bindings[binding_id={binding['binding_id']}].canonical_to_evidence_paths",
            )
        canonical_value = _require_one(
            resolve_path(canonical, canonical_path),
            path=str(binding["canonical_artifact_path"]),
            json_path=canonical_path,
        )
        evidence_value = _require_one(
            resolve_path(document, evidence_path_name),
            path=relative,
            json_path=evidence_path_name,
        )
        if evidence_value != canonical_value:
            raise ArtifactBindingError(
                f"canonical field {canonical_path}={canonical_value!r} does not match evidence",
                path=relative,
                json_path=evidence_path_name,
            )

    for evidence_path_name, expected in (surface.get("required_evidence_equal") or {}).items():
        actual = _require_one(
            resolve_path(document, str(evidence_path_name)),
            path=relative,
            json_path=str(evidence_path_name),
        )
        if actual != expected:
            raise ArtifactBindingError(
                f"required evidence field {evidence_path_name}={actual!r} expected {expected!r}",
                path=relative,
                json_path=str(evidence_path_name),
            )

    current_nodes = _collect_values(
        document,
        surface.get("current_identity_paths") or [],
        file_path=relative,
    ) if surface.get("current_identity_paths") else []
    superseded_nodes = _collect_values(
        document,
        surface.get("superseded_identity_paths") or [],
        file_path=relative,
    )
    superseded_hashes = _as_hash_set(value for _, value in superseded_nodes)

    if surface.get("role") == "current":
        if not current_nodes:
            raise ArtifactBindingError(
                "current-role surface has no current identity paths",
                path=relative,
            )
        for resolved, value in current_nodes:
            if value != current_identity:
                raise ArtifactBindingError(
                    f"stale current identity {value} expected {current_identity}",
                    path=relative,
                    json_path=resolved,
                )
            if value in superseded_hashes:
                raise ArtifactBindingError(
                    "current identity is incorrectly listed as superseded",
                    path=relative,
                    json_path=resolved,
                )
        for resolved, value in superseded_nodes:
            hashes = _as_hash_set([value])
            if current_identity in hashes:
                raise ArtifactBindingError(
                    "current identity is incorrectly listed as superseded",
                    path=relative,
                    json_path=resolved,
                )
            if hashes & {current_identity}:
                raise ArtifactBindingError(
                    "current identity is incorrectly listed as superseded",
                    path=relative,
                    json_path=resolved,
                )
        for json_path in surface.get("narrative_paths") or []:
            nodes = resolve_path(document, json_path)
            if not nodes:
                raise ArtifactBindingError("missing JSON path", path=relative, json_path=json_path)
            for resolved, text in nodes:
                if not isinstance(text, str):
                    raise ArtifactBindingError(
                        "narrative path is not a string",
                        path=relative,
                        json_path=resolved,
                    )
                for pattern in surface.get("narrative_current_patterns") or []:
                    for match in re.findall(pattern, text):
                        if match != current_identity:
                            raise ArtifactBindingError(
                                f"stale narrative identity {match} expected {current_identity}",
                                path=relative,
                                json_path=resolved,
                            )
    elif surface.get("role") == "historical":
        for resolved, value in current_nodes:
            if value == current_identity:
                raise ArtifactBindingError(
                    "historical surface presents the current identity as a live bind",
                    path=relative,
                    json_path=resolved,
                )
        for resolved, value in superseded_nodes:
            if value == current_identity:
                raise ArtifactBindingError(
                    "historical superseded path was overwritten with the current identity",
                    path=relative,
                    json_path=resolved,
                )
    else:
        raise ArtifactBindingError(
            f"unsupported evidence role {surface.get('role')!r}",
            path=relative,
        )

    for json_path in surface.get("lane_decision_paths") or []:
        for resolved, value in resolve_path(document, json_path):
            if value in set(binding.get("forbidden_lane_values") or []):
                raise ArtifactBindingError(
                    f"lane decision {value!r} is not allowed",
                    path=relative,
                    json_path=resolved,
                )
            required_lane = (binding.get("required_equal") or {}).get("lane_decision")
            if required_lane and value != required_lane:
                raise ArtifactBindingError(
                    f"lane decision {value!r} expected {required_lane!r}",
                    path=relative,
                    json_path=resolved,
                )
    for json_path in surface.get("forbidden_true_paths") or []:
        for resolved, value in resolve_path(document, json_path):
            if value is True:
                raise ArtifactBindingError(
                    "forbidden production or protected authority claim is true",
                    path=relative,
                    json_path=resolved,
                )

    if surface.get("role") == "current":
        output_nodes = resolve_path(document, "outputs[path=" + str(binding["canonical_artifact_path"]) + "]")
        for resolved, item in output_nodes:
            if not isinstance(item, Mapping):
                continue
            expected_sha = sha256_file(repo_root / str(binding["canonical_artifact_path"]))
            actual_sha = item.get("sha256")
            if actual_sha and actual_sha != expected_sha:
                raise ArtifactBindingError(
                    f"canonical artifact sha256 {actual_sha} expected {expected_sha}",
                    path=relative,
                    json_path=f"{resolved}.sha256",
                )
            actual_bytes = item.get("bytes")
            if actual_bytes is not None and int(actual_bytes) != (
                repo_root / str(binding["canonical_artifact_path"])
            ).stat().st_size:
                raise ArtifactBindingError(
                    f"canonical artifact bytes {actual_bytes} do not match the file",
                    path=relative,
                    json_path=f"{resolved}.bytes",
                )
            if item.get("artifact_identity") not in {None, current_identity}:
                raise ArtifactBindingError(
                    f"output artifact_identity {item.get('artifact_identity')} expected {current_identity}",
                    path=relative,
                    json_path=f"{resolved}.artifact_identity",
                )


def validate_artifact_bindings(repo_root: Path, contract: Mapping[str, Any] | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    contract = dict(contract or load_contract(repo_root))
    report: dict[str, Any] = {"bindings": [], "result": "PASS"}
    for binding in contract.get("bindings") or []:
        payload, identity = _validate_canonical(repo_root, binding)
        for surface in binding.get("evidence_surfaces") or []:
            _validate_surface(repo_root, binding, surface, payload, identity)
        report["bindings"].append(
            {
                "binding_id": binding.get("binding_id"),
                "canonical_artifact_path": binding.get("canonical_artifact_path"),
                "identity": identity,
            }
        )
    return report

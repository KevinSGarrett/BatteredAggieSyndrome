from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .contracts import canonical_json_bytes, sha256_value
from .controller_state import ControllerState, TERMINAL_STATES, rfc3339
from .cpu_worker_backend import MAX_RECORDS
from .orchestration import (
    ATOMIC_EXECUTABLE,
    ReadyWorkInventory,
    ReadyWorkUnit,
    RouteDecision,
    RoutingDisposition,
    validate_work_unit_roles,
)


MAX_DISCOVERED_MANIFEST_BYTES = 1024 * 1024
MAX_DISCOVERED_UNITS = 64
MAX_PROVIDER_WORK_BYTES = 2 * 1024 * 1024
MAX_PROVIDER_WORK_UNITS = 64
MAX_PROVIDER_WORK_SCAN_UNITS = 4096
MAX_PROVIDER_WORK_FILE_VISITS = 65536
MAX_HISTORICAL_MANIFEST_SCAN_UNITS = 65536
MAX_OPENAI_CROSS_PROVIDER_QA_RESULTS_PER_PROVIDER = 16
DISCOVERY_NAMES = frozenset({"run.json", "progress.json"})
DYNAMIC_PREFIXES = (
    "AUTO-CPU-MANIFEST-",
    "AUTO-CPU-LINE-HASH-",
    "AUTO-CPU-TEXT-DEDUP-",
    "AUTO-BGE-",
    "AUTO-OAI-",
    "AUTO-OR-",
    "AUTO-CURSOR-",
)
CPU_MANIFEST_TASK_FORMAT = "cpu_worker_canonical_manifest_v1"
CPU_MANIFEST_SCHEMA_SHA256 = hashlib.sha256(
    b"cpu_worker_canonical_manifest_v1:value:any-json;candidate-only;exact-local-replay"
).hexdigest()
CPU_LINE_HASH_TASK_FORMAT = "cpu_worker_line_hash_manifest_v1"
CPU_LINE_HASH_SCHEMA_SHA256 = hashlib.sha256(
    b"cpu_worker_line_hash_manifest_v1:lines:utf8-list;candidate-only;exact-local-replay"
).hexdigest()
CPU_LINE_HASH_DOWNSTREAM_CONSUMER_VERSION = "historical-manifest-provenance-index-v1"
CPU_TEXT_DEDUP_TASK_FORMAT = "cpu_worker_exact_text_dedup_v1"
CPU_TEXT_DEDUP_SCHEMA_SHA256 = hashlib.sha256(
    b"cpu_worker_exact_text_dedup_v1:records:id-text;nfkc-whitespace-casefold;candidate-only"
).hexdigest()
CPU_EXACT_ROUTES = {
    "CANONICAL_JSON": (CPU_MANIFEST_TASK_FORMAT, CPU_MANIFEST_SCHEMA_SHA256, "AUTO-CPU-MANIFEST-"),
    "LINE_HASH_MANIFEST": (
        CPU_LINE_HASH_TASK_FORMAT,
        CPU_LINE_HASH_SCHEMA_SHA256,
        "AUTO-CPU-LINE-HASH-",
    ),
    "EXACT_TEXT_DEDUP": (
        CPU_TEXT_DEDUP_TASK_FORMAT,
        CPU_TEXT_DEDUP_SCHEMA_SHA256,
        "AUTO-CPU-TEXT-DEDUP-",
    ),
}
OPENROUTER_TASK_FORMAT = "governed_openrouter_candidate_v1"
CURSOR_TASK_FORMAT = "governed_cursor_repository_review_v1"
CURSOR_SCHEMA_SHA256 = hashlib.sha256(
    b"governed_cursor_repository_review_v1:exact-base;candidate-only;no-pr;no-authority"
).hexdigest()
CURSOR_IMPLEMENTATION_TASK_FORMAT = "governed_cursor_repository_implementation_v1"
CURSOR_IMPLEMENTATION_SCHEMA_SHA256 = hashlib.sha256(
    b"governed_cursor_repository_implementation_v1:exact-base;candidate-only;allowed-paths;no-pr;no-authority"
).hexdigest()
CURSOR_TASK_FORMATS = frozenset(
    {CURSOR_TASK_FORMAT, CURSOR_IMPLEMENTATION_TASK_FORMAT}
)
BGE_MODEL = "bge-m3:latest"
BGE_MODEL_DIGEST = "7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab"
BGE_TASK_FORMAT = "embedding_dedup_semantic_candidate_retrieval"


def _safe_cursor_repository_path(path: object) -> bool:
    if not isinstance(path, str) or not path or "\\" in path or path.startswith("/"):
        return False
    parts = path.split("/")
    name = parts[-1].lower()
    return (
        ".." not in parts
        and parts[0].lower() != ".git"
        and name != ".env"
        and not name.startswith(".env.")
        and not name.endswith((".pem", ".p12", ".pfx"))
    )
BGE_POLICY_VERSION = "unified-assistive-execution-plane-v2-operational-correction"
BGE_PROMPT_VERSION = "embedding-shadow-v1"
BGE_SCHEMA_VERSION = "1"
BGE_SCHEMA_SHA256 = "fd5ed573e9990a40674b28032a2b4fb63659c62423479c554188149826ea362c"
BGE_DOWNSTREAM_CONSUMER_VERSION = "bge-reconciliation-review-routing-v1"
# Only the exact local retrieval route has completed a saturated, zero-useful-value
# campaign with no remaining nonduplicate packet population.  Remote semantic and
# repository providers must remain admitted so that the producer can generate new
# real work and repair downstream consumption instead of turning a measurement
# failure into a global provider shutdown.
USEFUL_WORK_SATURATION_SUSPEND_PROVIDERS = frozenset({"ollama_local"})
READY_WORK_UNIT_FIELDS = frozenset(ReadyWorkUnit.__dataclass_fields__)
ROUTE_DECISION_FIELDS = frozenset(RouteDecision.__dataclass_fields__)


class _BoundedVisibleTextParser(HTMLParser):
    """Extract a deterministic, bounded evidence excerpt without external parsers."""

    def __init__(self, max_chars: int) -> None:
        super().__init__(convert_charrefs=True)
        self.max_chars = max_chars
        self.parts: list[str] = []
        self.characters = 0
        self.suppressed_depth = 0

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "template", "noscript"}:
            self.suppressed_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "template", "noscript"} and self.suppressed_depth:
            self.suppressed_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.suppressed_depth or self.characters >= self.max_chars:
            return
        value = " ".join(data.split())
        if not value:
            return
        remaining = self.max_chars - self.characters
        value = value[:remaining]
        self.parts.append(value)
        self.characters += len(value) + 1

    def text(self) -> str:
        return "\n".join(self.parts)[: self.max_chars]


def _bounded_html_text(raw: bytes, max_chars: int = 10000) -> str:
    parser = _BoundedVisibleTextParser(max_chars)
    parser.feed(raw.decode("utf-8", errors="replace"))
    parser.close()
    return parser.text()


def _dynamic_work_unit_id(packet: dict[str, Any], packet_sha256: str) -> str | None:
    """Return the exact durable identity for a producer-generated provider packet."""
    provider = packet.get("provider")
    task_format = packet.get("task_format")
    prefix: str | None = None
    if provider == "openai_direct" and task_format == "governed_openai_candidate_v1":
        prefix = "AUTO-OAI-"
    elif provider == "openrouter" and task_format == OPENROUTER_TASK_FORMAT:
        prefix = "AUTO-OR-"
    elif provider == "ollama_local" and task_format == BGE_TASK_FORMAT:
        prefix = "AUTO-BGE-"
    elif provider == "cursor" and task_format in CURSOR_TASK_FORMATS:
        prefix = "AUTO-CURSOR-"
    elif provider == "remote_cpu_worker":
        route = CPU_EXACT_ROUTES.get(str(packet.get("task", "")))
        if route is not None:
            prefix = route[2]
    return None if prefix is None else prefix + packet_sha256[:20]


def cpu_qualification_evidence_sha256(
    snapshot: dict[str, Any], task: str = "CANONICAL_JSON"
) -> str | None:
    if task not in CPU_EXACT_ROUTES:
        return None
    evidence = snapshot.get("external_evidence", {}).get("cpu_worker", {})
    if not evidence.get("qualified"):
        return None

    def valid_sha256(value: object) -> bool:
        text = str(value)
        return len(text) == 64 and all(character in "0123456789abcdef" for character in text)

    qualifications = evidence.get("qualifications", [])
    if not isinstance(qualifications, list):
        return None
    for qualification in qualifications:
        tasks = qualification.get("tasks") if isinstance(qualification, dict) else None
        if (
            isinstance(qualification, dict)
            and isinstance(tasks, list)
            and task in tasks
            and valid_sha256(qualification.get("evidence_sha256"))
            and valid_sha256(qualification.get("readiness_evidence_sha256"))
        ):
            return str(qualification["readiness_evidence_sha256"])
    return None


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _content_addressed_json(root: Path, category: str, payload: dict[str, Any]) -> tuple[Path, str]:
    data = canonical_json_bytes(payload) + b"\n"
    digest = hashlib.sha256(data).hexdigest()
    destination = root / category / "sha256" / digest / "packet.json"
    if destination.exists():
        if destination.read_bytes() != data:
            raise RuntimeError("RUNTIME_INVENTORY_CONTENT_ADDRESS_COLLISION")
    else:
        _atomic_write(destination, data)
    return destination, digest


def _verified_json(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise RuntimeError("RUNTIME_INVENTORY_REFERENCED_HASH_MISMATCH")
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise ValueError("RUNTIME_INVENTORY_JSON_NOT_OBJECT")
    return payload


def _bounded_json_scan(
    root: Path,
    *,
    limit: int,
    allowed_names: frozenset[str] | None = None,
) -> tuple[list[Path], bool]:
    """Traverse an allowlisted root without first materializing an unbounded tree."""
    if limit <= 0:
        raise ValueError("BOUNDED_JSON_SCAN_LIMIT_INVALID")
    resolved_root = root.resolve(strict=True)
    directories = [resolved_root]
    files: list[Path] = []
    visited_directories = 0
    directory_limit = max(1024, limit * 8)
    capped = False
    while directories and len(files) < limit:
        current = directories.pop()
        visited_directories += 1
        if visited_directories > directory_limit:
            capped = True
            break
        try:
            entries = sorted(os.scandir(current), key=lambda entry: entry.name, reverse=True)
        except OSError:
            raise
        for entry in entries:
            try:
                candidate = current / entry.name
                if entry.is_dir(follow_symlinks=False):
                    # Preserve the caller's canonical root spelling. Windows runners can
                    # return a long path from scandir beneath an 8.3-form temp root,
                    # causing an otherwise valid relative_to() check to fail.
                    directories.append(candidate)
                elif (
                    entry.is_file(follow_symlinks=False)
                    and entry.name.endswith(".json")
                    and (allowed_names is None or entry.name in allowed_names)
                ):
                    files.append(candidate)
                    if len(files) >= limit:
                        capped = bool(directories) or entries.index(entry) < len(entries) - 1
                        break
            except OSError:
                continue
    if directories:
        capped = True
    return sorted(files, key=lambda path: path.relative_to(resolved_root).as_posix()), capped


def _bounded_top_level_json_scan(
    root: Path,
    *,
    limit: int,
    name_prefix: str | None = None,
) -> tuple[list[Path], bool]:
    """Scan one explicit registry directory without traversing legacy subtrees."""
    if limit <= 0:
        raise ValueError("BOUNDED_TOP_LEVEL_JSON_SCAN_LIMIT_INVALID")
    resolved_root = root.resolve(strict=True)
    files: list[Path] = []
    capped = False
    for entry in sorted(os.scandir(resolved_root), key=lambda item: item.name):
        try:
            if not entry.is_file(follow_symlinks=False) or not entry.name.endswith(".json"):
                continue
            if name_prefix is not None and not entry.name.startswith(name_prefix):
                continue
            if len(files) >= limit:
                capped = True
                break
            # Construct from the resolved registry root rather than entry.path so
            # Windows short/long path aliases cannot escape the relative identity.
            files.append(resolved_root / entry.name)
        except OSError:
            continue
    return files, capped


def _bounded_distinct_json_scan(
    root: Path,
    *,
    limit: int,
    file_visit_limit: int,
) -> tuple[list[Path], bool, int]:
    """Bound traversal by visited files while duplicate bytes consume one slot."""
    if limit <= 0 or file_visit_limit < limit:
        raise ValueError("BOUNDED_DISTINCT_JSON_SCAN_LIMIT_INVALID")
    resolved_root = root.resolve(strict=True)
    directories = [resolved_root]
    selected: list[Path] = []
    seen_digests: set[str] = set()
    visited_files = 0
    visited_directories = 0
    directory_limit = max(1024, file_visit_limit * 2)
    capped = False
    while directories and len(selected) < limit and visited_files < file_visit_limit:
        current = directories.pop()
        visited_directories += 1
        if visited_directories > directory_limit:
            capped = True
            break
        entries = sorted(os.scandir(current), key=lambda entry: entry.name, reverse=True)
        for index, entry in enumerate(entries):
            try:
                candidate = current / entry.name
                if entry.is_dir(follow_symlinks=False):
                    directories.append(candidate)
                    continue
                if not entry.is_file(follow_symlinks=False) or not entry.name.endswith(".json"):
                    continue
                visited_files += 1
                size = entry.stat(follow_symlinks=False).st_size
                if 0 < size <= MAX_PROVIDER_WORK_BYTES:
                    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
                else:
                    digest = "PATH:" + candidate.relative_to(resolved_root).as_posix()
                if digest not in seen_digests:
                    seen_digests.add(digest)
                    selected.append(candidate)
                if len(selected) >= limit or visited_files >= file_visit_limit:
                    capped = bool(directories) or index < len(entries) - 1
                    break
            except OSError:
                continue
    if directories:
        capped = True
    return (
        sorted(selected, key=lambda path: path.relative_to(resolved_root).as_posix()),
        capped,
        visited_files,
    )


@dataclass(frozen=True)
class RuntimeInventoryConfig:
    current_path: Path
    snapshot_root: Path
    packet_root: Path
    manifests_root: Path
    provider_work_root: Path | None = None
    release_root: Path | None = None
    build_commit: str | None = None
    semantic_materializer_path: Path | None = None
    semantic_policy_path: Path | None = None
    semantic_readiness_path: Path | None = None
    openrouter_task_registry_path: Path | None = None
    openai_task_registry_path: Path | None = None
    external_assistive_root: Path | None = None
    continuous_source_root: Path | None = None
    project_root: Path | None = None
    bge_downstream_consumer_contract_version: str | None = None
    refresh_max_age_seconds: int = 240

    def validate(self) -> None:
        if self.refresh_max_age_seconds <= 0:
            raise ValueError("RUNTIME_INVENTORY_REFRESH_AGE_INVALID")
        if not self.manifests_root.is_absolute():
            raise ValueError("RUNTIME_INVENTORY_MANIFEST_ROOT_NOT_ABSOLUTE")
        if self.provider_work_root is not None and not self.provider_work_root.is_absolute():
            raise ValueError("RUNTIME_INVENTORY_PROVIDER_WORK_ROOT_NOT_ABSOLUTE")
        if self.continuous_source_root is not None and not self.continuous_source_root.is_absolute():
            raise ValueError("RUNTIME_INVENTORY_CONTINUOUS_SOURCE_ROOT_NOT_ABSOLUTE")
        if self.project_root is not None and not self.project_root.is_absolute():
            raise ValueError("RUNTIME_INVENTORY_PROJECT_ROOT_NOT_ABSOLUTE")
        if self.bge_downstream_consumer_contract_version is not None and (
            not self.bge_downstream_consumer_contract_version.strip()
            or len(self.bge_downstream_consumer_contract_version) > 128
        ):
            raise ValueError("RUNTIME_INVENTORY_BGE_CONSUMER_CONTRACT_INVALID")
        if (self.release_root is None) != (self.build_commit is None):
            raise ValueError("RUNTIME_INVENTORY_RELEASE_IDENTITY_INCOMPLETE")
        if self.release_root is not None and not self.release_root.is_absolute():
            raise ValueError("RUNTIME_INVENTORY_RELEASE_ROOT_NOT_ABSOLUTE")
        if self.build_commit is not None and (
            len(self.build_commit) != 40
            or any(character not in "0123456789abcdef" for character in self.build_commit)
        ):
            raise ValueError("RUNTIME_INVENTORY_BUILD_COMMIT_INVALID")
        semantic_paths = (
            self.semantic_materializer_path,
            self.semantic_policy_path,
            self.semantic_readiness_path,
            self.external_assistive_root,
        )
        if any(path is not None for path in semantic_paths) and not all(
            path is not None for path in semantic_paths
        ):
            raise ValueError("RUNTIME_INVENTORY_SEMANTIC_REFRESH_CONFIG_INCOMPLETE")
        if any(path is not None and not path.is_absolute() for path in semantic_paths):
            raise ValueError("RUNTIME_INVENTORY_SEMANTIC_REFRESH_PATH_NOT_ABSOLUTE")
        if (
            self.openrouter_task_registry_path is not None
            and not self.openrouter_task_registry_path.is_absolute()
        ):
            raise ValueError("RUNTIME_INVENTORY_OPENROUTER_TASK_REGISTRY_NOT_ABSOLUTE")
        if (
            self.openai_task_registry_path is not None
            and not self.openai_task_registry_path.is_absolute()
        ):
            raise ValueError("RUNTIME_INVENTORY_OPENAI_TASK_REGISTRY_NOT_ABSOLUTE")


class RuntimeInventoryRefresher:
    """Derive immutable granular work from real external manifests and refresh a small pointer."""

    def __init__(self, state: ControllerState, config: RuntimeInventoryConfig) -> None:
        config.validate()
        self.state = state
        self.config = config
        self._semantic_module: Any | None = None
        self._openrouter_task_registry: dict[str, Any] | None = None
        self._jira_ready_cache: list[tuple[Path, dict[str, Any], str]] | None = None
        self._openai_task_registry: dict[str, Any] | None = None
        self._provider_packet_findings: list[dict[str, str]] = []

    def _openrouter_jira_identity(self, task_id: str) -> str:
        """Resolve the exact task/Jira binding from the versioned provider registry."""
        if self._openrouter_task_registry is None:
            path = self.config.openrouter_task_registry_path
            if path is None or not path.is_file():
                raise RuntimeError("RUNTIME_INVENTORY_OPENROUTER_TASK_REGISTRY_MISSING")
            registry = _verified_json(path)
            if registry.get("schema_version") != 1 or not isinstance(registry.get("tasks"), dict):
                raise ValueError("RUNTIME_INVENTORY_OPENROUTER_TASK_REGISTRY_INVALID")
            self._openrouter_task_registry = registry
        task = self._openrouter_task_registry["tasks"].get(task_id)
        if not isinstance(task, dict):
            raise ValueError("RUNTIME_INVENTORY_OPENROUTER_TASK_NOT_REGISTERED")
        jira_unit = task.get("jira_unit")
        if not isinstance(jira_unit, str) or not jira_unit:
            raise ValueError("RUNTIME_INVENTORY_OPENROUTER_TASK_JIRA_IDENTITY_INVALID")
        return jira_unit

    def _openai_task_definition(self, task_id: str) -> dict[str, Any]:
        if self._openai_task_registry is None:
            path = self.config.openai_task_registry_path
            if path is None or not path.is_file():
                raise RuntimeError("RUNTIME_INVENTORY_OPENAI_TASK_REGISTRY_MISSING")
            registry = _verified_json(path)
            if registry.get("schema_version") != 2 or not isinstance(registry.get("tasks"), dict):
                raise ValueError("RUNTIME_INVENTORY_OPENAI_TASK_REGISTRY_INVALID")
            self._openai_task_registry = registry
        task = self._openai_task_registry["tasks"].get(task_id)
        if not isinstance(task, dict):
            raise ValueError("RUNTIME_INVENTORY_OPENAI_TASK_NOT_REGISTERED")
        return task

    def _load_semantic_module(self) -> Any:
        if self._semantic_module is not None:
            return self._semantic_module
        path = self.config.semantic_materializer_path
        if path is None or not path.is_file():
            raise RuntimeError("RUNTIME_INVENTORY_SEMANTIC_MATERIALIZER_MISSING")
        spec = importlib.util.spec_from_file_location("aggie_runtime_semantic_materializer", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("RUNTIME_INVENTORY_SEMANTIC_MATERIALIZER_IMPORT_INVALID")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        required = (
            "external_evidence_identity",
            "openrouter_semantic_evidence",
            "cursor_semantic_evidence",
            "local_qwen_semantic_evidence",
            "cpu_worker_semantic_evidence",
        )
        if any(not callable(getattr(module, name, None)) for name in required):
            raise RuntimeError("RUNTIME_INVENTORY_SEMANTIC_MATERIALIZER_CONTRACT_INVALID")
        self._semantic_module = module
        return module

    def _live_external_evidence(self, base: dict[str, Any]) -> dict[str, Any]:
        if self.config.semantic_materializer_path is None:
            return dict(base.get("external_evidence", {}))
        assert self.config.semantic_policy_path is not None
        assert self.config.semantic_readiness_path is not None
        assert self.config.external_assistive_root is not None
        module = self._load_semantic_module()
        policy = _verified_json(self.config.semantic_policy_path)
        readiness = _verified_json(self.config.semantic_readiness_path)
        assistive_root = self.config.external_assistive_root
        data_root = assistive_root.parent
        cursor_evidence = module.cursor_semantic_evidence(assistive_root / "cursor")
        cursor_budget = policy.get("budgets", {}).get("cursor", {})
        if isinstance(cursor_budget, dict):
            cursor_evidence = {
                **cursor_evidence,
                "budget_hard_limit_usd": str(cursor_budget.get("hard_limit_usd", "0")),
                "budget_released_stage_usd": str(
                    cursor_budget.get("released_stage_usd", "0")
                ),
            }
        return {
            "openai": module.external_evidence_identity(data_root / "openai"),
            "openrouter": module.openrouter_semantic_evidence(assistive_root / "openrouter", policy),
            "cursor": cursor_evidence,
            "local_qwen": module.local_qwen_semantic_evidence(assistive_root / "local_qwen", readiness),
            "cpu_worker": module.cpu_worker_semantic_evidence(assistive_root / "cpu_worker"),
        }

    def _load_current_snapshot(self) -> tuple[dict[str, Any], str]:
        payload = _verified_json(self.config.current_path)
        if payload.get("artifact_type") == "UNIFIED_ASSISTIVE_INVENTORY_POINTER":
            snapshot_path = Path(str(payload["snapshot_path"]))
            snapshot_sha256 = str(payload["snapshot_sha256"])
            return _verified_json(snapshot_path, snapshot_sha256), snapshot_sha256
        data = self.config.current_path.read_bytes()
        return payload, hashlib.sha256(data).hexdigest()

    def _deployed_release(self) -> dict[str, Any] | None:
        if self.config.release_root is None or self.config.build_commit is None:
            return None
        release = self.config.release_root.resolve(strict=True)
        if release.name != self.config.build_commit:
            raise RuntimeError("RUNTIME_INVENTORY_RELEASE_DIRECTORY_BUILD_MISMATCH")
        manifest_path = release / "RELEASE_MANIFEST.json"
        manifest_data = manifest_path.read_bytes()
        manifest = json.loads(manifest_data)
        if manifest.get("build_commit") != self.config.build_commit:
            raise RuntimeError("RUNTIME_INVENTORY_RELEASE_MANIFEST_BUILD_MISMATCH")
        return {
            "build_commit": self.config.build_commit,
            "release_root": str(release),
            "release_manifest_sha256": hashlib.sha256(manifest_data).hexdigest(),
            "source_tree_sha256": manifest.get("source_tree_sha256"),
            "evidence_scope": "IMMUTABLE_DEPLOYED_RELEASE_FROM_MERGED_MAIN",
        }

    def _jira_ready_records(self, *, limit: int = 16) -> list[tuple[Path, dict[str, Any], str]]:
        """Return bounded, explicitly executable canonical Jira units."""
        if self._jira_ready_cache is not None:
            return self._jira_ready_cache[:limit]
        project_root = self.config.project_root
        if project_root is None:
            return []
        records_root = project_root / "jira" / "records" / "issues"
        if not records_root.is_dir():
            return []
        candidates, capped = _bounded_json_scan(
            records_root,
            limit=MAX_PROVIDER_WORK_SCAN_UNITS,
        )
        if capped:
            raise RuntimeError("RUNTIME_INVENTORY_JIRA_READY_SCAN_BOUND_EXCEEDED")
        priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        ready: list[tuple[int, str, Path, dict[str, Any], str]] = []
        for path in candidates:
            raw = path.read_bytes()
            if not 0 < len(raw) <= MAX_PROVIDER_WORK_BYTES:
                continue
            record = json.loads(raw)
            if not isinstance(record, dict):
                continue
            live_status = str(record.get("operational_jira", {}).get("status_raw", "")).upper()
            if (
                record.get("ready") is not True
                or record.get("workflow_state") != "READY"
                or record.get("execution_mode") != "ATOMIC_EXECUTION"
                or bool(str(record.get("blocked_reason", "")).strip())
                or live_status in {"DONE", "CLOSED", "RESOLVED"}
                or not record.get("jira_key")
                or not record.get("local_id")
                or not record.get("acceptance_criteria")
                or not (
                    record.get("allowed_modification_paths")
                    or record.get("files_expected_to_be_touched")
                    or record.get("expected_outputs")
                )
            ):
                continue
            source_sha256 = hashlib.sha256(raw).hexdigest()
            ready.append(
                (
                    priority_rank.get(str(record.get("priority", "P3")), 9),
                    str(record["local_id"]),
                    path,
                    record,
                    source_sha256,
                )
            )
        ready.sort(key=lambda item: (item[0], item[1], item[2].as_posix()))
        self._jira_ready_cache = [
            (path, record, digest) for _, _, path, record, digest in ready
        ]
        return self._jira_ready_cache[:limit]

    def _discover(self, moment: datetime) -> list[tuple[ReadyWorkUnit, RouteDecision, dict[str, Any]]]:
        root = self.config.manifests_root.resolve(strict=True)
        candidates, scan_capped = _bounded_json_scan(
            root,
            limit=MAX_PROVIDER_WORK_SCAN_UNITS,
            allowed_names=DISCOVERY_NAMES,
        )
        discovered: list[tuple[ReadyWorkUnit, RouteDecision, dict[str, Any]]] = []
        now = rfc3339(moment)
        if scan_capped:
            finding = {
                "finding": "RUNTIME_INVENTORY_SEMANTIC_DISCOVERY_SCAN_CAPACITY_DEFERRED",
                "observed_at": now,
                "disposition": "BOUNDED_SCAN_CONTINUES_WITH_PER_FILE_ISOLATION",
            }
            self.state.append_event("SEMANTIC_DISCOVERY_CAPACITY_DEFERRED", finding, now=moment)
        for source in candidates:
            try:
                resolved = source.resolve(strict=True)
                if root not in resolved.parents:
                    raise RuntimeError("RUNTIME_INVENTORY_SOURCE_OUTSIDE_ALLOWLIST")
                if not 0 < resolved.stat().st_size <= MAX_DISCOVERED_MANIFEST_BYTES:
                    raise ValueError("RUNTIME_INVENTORY_DISCOVERY_SOURCE_SIZE_INVALID")
                raw = resolved.read_bytes()
                source_sha256 = hashlib.sha256(raw).hexdigest()
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise ValueError("RUNTIME_INVENTORY_DISCOVERY_SOURCE_NOT_OBJECT")
                relative = resolved.relative_to(root).as_posix()
            except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                finding = {
                    "finding": type(exc).__name__ + ":" + str(exc)[:240],
                    "observed_at": now,
                    "source_relative_path": source.relative_to(root).as_posix(),
                    "disposition": "SOURCE_ISOLATED_UNRELATED_DISCOVERY_CONTINUES",
                }
                self.state.append_event("SEMANTIC_DISCOVERY_SOURCE_ISOLATED", finding, now=moment)
                continue
            packet = {
                "schema_version": 1,
                "artifact_type": "CPU_WORKER_CANONICAL_MANIFEST_PACKET",
                "task": "CANONICAL_JSON",
                "task_format": CPU_MANIFEST_TASK_FORMAT,
                "jira_unit": "BAT-563",
                "source_path": str(resolved),
                "source_relative_path": relative,
                "source_sha256": source_sha256,
                "payload": {"value": value},
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            packet_path, packet_sha256 = _content_addressed_json(self.config.packet_root, "packets", packet)
            work_unit_id = f"AUTO-CPU-MANIFEST-{packet_sha256[:20]}"
            unit = ReadyWorkUnit(
                work_unit_id=work_unit_id,
                jira_unit="BAT-563",
                task_format=CPU_MANIFEST_TASK_FORMAT,
                schema_sha256=CPU_MANIFEST_SCHEMA_SHA256,
                authority="CANDIDATE_ONLY",
                source_hashes=(source_sha256, packet_sha256),
                dependencies=(),
                pre_routing_effort_points=1,
                scope=f"Exact canonicalization and provenance QA for external manifest {relative}",
            )
            decision = RouteDecision(
                work_unit_id=work_unit_id,
                work_unit_identity=unit.identity(),
                disposition=RoutingDisposition.REMOTE_CPU_WORKER,
                provider="remote_cpu_worker",
                model="DETERMINISTIC_CPU_WORKER_V2",
                reason="EXACT_CPU_WORKER_QUALIFICATION_PASS_MANIFEST_QA",
                decided_at=now,
            )
            discovered.append(
                (unit, decision, {"packet_path": str(packet_path), "packet_sha256": packet_sha256})
            )
        states = self.state.work_unit_states({unit.work_unit_id for unit, _, _ in discovered})
        active = [
            entry
            for entry in discovered
            if states.get(entry[0].work_unit_id) not in TERMINAL_STATES
        ]
        if len(active) > MAX_DISCOVERED_UNITS:
            finding = {
                "finding": "RUNTIME_INVENTORY_SEMANTIC_DISCOVERY_ACTIVE_CAPACITY_DEFERRED",
                "observed_at": now,
                "active_units": len(active),
                "admitted_units": MAX_DISCOVERED_UNITS,
                "disposition": "EXCESS_ACTIVE_UNITS_REMAIN_DISCOVERABLE",
            }
            self.state.append_event("SEMANTIC_DISCOVERY_CAPACITY_DEFERRED", finding, now=moment)
            active = active[:MAX_DISCOVERED_UNITS]
        return active

    @staticmethod
    def _valid_sha256(value: object) -> bool:
        text = str(value)
        return len(text) == 64 and all(character in "0123456789abcdef" for character in text)

    @staticmethod
    def _valid_commit(value: object) -> bool:
        text = str(value)
        return len(text) == 40 and all(character in "0123456789abcdef" for character in text)

    @classmethod
    def _snapshot_release_commit(cls, snapshot: dict[str, Any]) -> str:
        git = snapshot.get("git") or {}
        release = snapshot.get("deployed_release") or {}
        values = [
            git.get("origin_main"),
            git.get("head"),
            git.get("deployed_head"),
            git.get("merged_main_identity_at_release_build"),
            release.get("build_commit"),
        ]
        present = [str(value) for value in values if value is not None]
        if not present or any(not cls._valid_commit(value) for value in present):
            raise RuntimeError("RUNTIME_INVENTORY_RELEASE_IDENTITY_INVALID")
        identities = set(present)
        if len(identities) != 1:
            raise RuntimeError("RUNTIME_INVENTORY_RELEASE_IDENTITY_CONFLICT")
        return identities.pop()

    @classmethod
    def _execution_packet_revision_metadata(
        cls,
        reference: dict[str, Any],
        release_commit: str,
    ) -> dict[str, Any]:
        """Bind an execution reference to the exact repository revision it was built for."""
        if not isinstance(reference, dict):
            raise ValueError("RUNTIME_INVENTORY_EXECUTION_REFERENCE_INVALID")
        packet_path = Path(str(reference.get("packet_path", "")))
        packet_sha256 = str(reference.get("packet_sha256", ""))
        if not packet_path.is_file() or not cls._valid_sha256(packet_sha256):
            raise RuntimeError("RUNTIME_INVENTORY_EXECUTION_PACKET_REFERENCE_INVALID")
        raw = packet_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != packet_sha256:
            raise RuntimeError("RUNTIME_INVENTORY_EXECUTION_PACKET_HASH_MISMATCH")
        packet = json.loads(raw)
        if not isinstance(packet, dict):
            raise ValueError("RUNTIME_INVENTORY_EXECUTION_PACKET_NOT_OBJECT")
        packet_base = packet.get("base_commit")
        preserved_source_commit = reference.get("source_commit")
        if packet_base is not None:
            if not cls._valid_commit(packet_base):
                raise ValueError("RUNTIME_INVENTORY_EXECUTION_PACKET_BASE_COMMIT_INVALID")
            source_commit = str(packet_base)
            if preserved_source_commit is not None and preserved_source_commit != source_commit:
                raise RuntimeError("RUNTIME_INVENTORY_EXECUTION_SOURCE_COMMIT_CONFLICT")
        elif preserved_source_commit is not None:
            if not cls._valid_commit(preserved_source_commit):
                raise ValueError("RUNTIME_INVENTORY_EXECUTION_SOURCE_COMMIT_INVALID")
            source_commit = str(preserved_source_commit)
        else:
            source_commit = release_commit
        source_jira_unit = packet.get("source_jira_unit")
        family_material: dict[str, Any] = {
            "provider": packet.get("provider", "remote_cpu_worker"),
            "task_format": packet.get("task_format"),
            "jira_unit": source_jira_unit or packet.get("jira_unit"),
        }
        if source_jira_unit is None:
            family_material["scope"] = packet.get("scope")
        elif packet.get("task_format") == CURSOR_IMPLEMENTATION_TASK_FORMAT:
            family_material["allowed_paths"] = packet.get("allowed_paths")
            family_material["required_tests"] = packet.get("required_tests")
        return {
            **reference,
            "source_commit": source_commit,
            "revision_family_identity": sha256_value(family_material),
        }

    @classmethod
    def _derive_revision_supersessions(
        cls,
        *,
        execution_packets: dict[str, dict[str, Any]],
        execution_states: dict[str, str],
        release_commit: str,
        prior: list[dict[str, Any]],
        observed_at: str,
    ) -> list[dict[str, Any]]:
        """Preserve immutable old-base -> current-base replacement evidence."""
        records = {
            str(item.get("supersession_identity")): item
            for item in prior
            if isinstance(item, dict) and cls._valid_sha256(item.get("supersession_identity"))
        }
        by_family: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for work_unit_id, reference in execution_packets.items():
            family = str(reference.get("revision_family_identity", ""))
            if cls._valid_sha256(family):
                by_family.setdefault(family, []).append((work_unit_id, reference))
        for family, entries in by_family.items():
            current = [
                item for item in entries
                if item[1].get("source_commit") == release_commit
            ]
            prior_entries = [
                item for item in entries
                if item[1].get("source_commit") != release_commit
                and execution_states.get(item[0]) in TERMINAL_STATES
            ]
            for old_id, old_reference in prior_entries:
                for new_id, new_reference in current:
                    if old_id == new_id:
                        continue
                    material = {
                        "revision_family_identity": family,
                        "superseded_work_unit_id": old_id,
                        "superseding_work_unit_id": new_id,
                        "superseded_packet_sha256": old_reference.get("packet_sha256"),
                        "superseding_packet_sha256": new_reference.get("packet_sha256"),
                        "superseded_source_commit": old_reference.get("source_commit"),
                        "superseding_source_commit": release_commit,
                        "reason": "SOURCE_COMMIT_TRANSITION_REQUIRES_FRESH_PROVIDER_DISPATCH",
                    }
                    identity = sha256_value(material)
                    records.setdefault(
                        identity,
                        {
                            **material,
                            "supersession_identity": identity,
                            "recorded_at": observed_at,
                        },
                    )
        return [records[key] for key in sorted(records)]

    @classmethod
    def _cursor_review_matches_release(
        cls,
        packet: object,
        release_commit: str,
    ) -> bool:
        return bool(
            isinstance(packet, dict)
            and packet.get("task_format") == CURSOR_TASK_FORMAT
            and isinstance(packet.get("source_jira_unit"), str)
            and packet.get("base_commit") == release_commit
            and packet.get("starting_ref") == release_commit
        )

    def _load_routed_cursor_review_packet(
        self,
        candidate: dict[str, Any],
    ) -> tuple[dict[str, Any], str] | None:
        """Load a review packet only through its immutable routing chain."""
        packet_sha256 = candidate.get("routed_packet_sha256")
        request_artifact_sha256 = candidate.get("request_artifact_sha256")
        if not self._valid_sha256(packet_sha256) or not self._valid_sha256(
            request_artifact_sha256
        ):
            return None
        request_path = Path(str(candidate.get("request_artifact_path", "")))
        if not request_path.is_file():
            return None
        request_raw = request_path.read_bytes()
        if hashlib.sha256(request_raw).hexdigest() != request_artifact_sha256:
            return None
        try:
            request = json.loads(request_raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(request, dict) or any(
            (
                request.get("artifact_type") != "GOVERNED_CURSOR_DISPATCH_REQUEST",
                request.get("provider") != "cursor",
                request.get("authority") != "CANDIDATE_ONLY",
                request.get("work_unit_id") != candidate.get("work_unit_id"),
                request.get("attempt_id") != candidate.get("attempt_id"),
                request.get("packet_sha256") != packet_sha256,
            )
        ):
            return None
        packet_path = (
            self.config.packet_root
            / "provider-packets"
            / "sha256"
            / str(packet_sha256)
            / "packet.json"
        )
        if not packet_path.is_file():
            return None
        packet_raw = packet_path.read_bytes()
        if hashlib.sha256(packet_raw).hexdigest() != packet_sha256:
            return None
        try:
            packet = json.loads(packet_raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return (packet, str(packet_sha256)) if isinstance(packet, dict) else None

    @classmethod
    def _provider_readiness(cls, snapshot: dict[str, Any], packet: dict[str, Any]) -> str | None:
        provider = packet.get("provider")
        if provider == "remote_cpu_worker":
            task = str(packet.get("task", ""))
            route = CPU_EXACT_ROUTES.get(task)
            if route is not None and packet.get("task_format") == route[0]:
                return cpu_qualification_evidence_sha256(snapshot, task)
        if provider == "openai_direct":
            evidence = snapshot.get("external_evidence", {}).get("openai", {})
            digest = evidence.get("manifest_sha256")
            return str(digest) if evidence.get("present") and cls._valid_sha256(digest) else None
        if provider == "ollama_local" and packet.get("task_format") == "embedding_dedup_semantic_candidate_retrieval":
            routes = snapshot.get("external_evidence", {}).get("local_qwen", {}).get("routes", [])
            for route in routes if isinstance(routes, list) else []:
                exact = (
                    route.get("provider") == "ollama_local"
                    and route.get("resolved_model") == packet.get("model")
                    and route.get("model_digest") == packet.get("model_digest")
                    and route.get("task_format") == packet.get("task_format")
                    and route.get("policy_version") == packet.get("policy_version")
                    and route.get("prompt_version") == packet.get("prompt_version")
                    and route.get("schema_version") == packet.get("route_schema_version")
                    and route.get("schema_sha256") == packet.get("schema_sha256")
                )
                if exact and route.get("evidence_supported_state") == "READY" and route.get("evidence_verified") is True:
                    digest = route.get("evidence_sha256")
                    return str(digest) if cls._valid_sha256(digest) else None
        if provider == "openrouter" and packet.get("task_format") == OPENROUTER_TASK_FORMAT:
            routes = snapshot.get("external_evidence", {}).get("openrouter", {}).get("routes", [])
            for route in routes if isinstance(routes, list) else []:
                exact = (
                    route.get("provider") == "openrouter"
                    and route.get("task_format") == OPENROUTER_TASK_FORMAT
                    and route.get("task_id") == packet.get("task_id")
                    and route.get("schema_sha256") == packet.get("schema_sha256")
                    and route.get("request_schema_version") == packet.get("request_schema_version")
                    and route.get("provider_policy_version") == packet.get("provider_policy_version")
                    and route.get("model") == packet.get("model")
                    and route.get("reasoning_effort") == packet.get("reasoning_effort")
                )
                if not exact:
                    continue
                readiness = route.get("readiness_evidence_sha256")
                route_evidence = route.get("route_evidence_sha256")
                budget = route.get("budget_evidence_sha256")
                if (
                    route.get("readiness_supported_state") != "READY"
                    or route.get("evidence_verified") is not True
                    or not cls._valid_sha256(readiness)
                    or not cls._valid_sha256(route_evidence)
                    or not cls._valid_sha256(budget)
                ):
                    continue
                try:
                    released_stage_usd = Decimal(str(route.get("budget_released_stage_usd", "0")))
                    remaining_usd = Decimal(str(route.get("budget_remaining_usd", "0")))
                except InvalidOperation:
                    continue
                if released_stage_usd <= Decimal("0") or remaining_usd <= Decimal("0"):
                    continue
                return sha256_value(
                    {
                        "readiness_evidence_sha256": str(readiness),
                        "route_evidence_sha256": str(route_evidence),
                        "budget_evidence_sha256": str(budget),
                        "budget_remaining_usd": format(remaining_usd, "f"),
                    }
                )
        if provider == "cursor" and packet.get("task_format") in CURSOR_TASK_FORMATS:
            evidence = snapshot.get("external_evidence", {}).get("cursor", {})
            digest = evidence.get("manifest_sha256")
            try:
                settled = Decimal(str(evidence.get("settled_usd", "0")))
                released_stage = Decimal(
                    str(evidence.get("budget_released_stage_usd", "20.00"))
                )
                hard_limit = Decimal(str(evidence.get("budget_hard_limit_usd", "200.00")))
            except InvalidOperation:
                return None
            if (
                evidence.get("present") is True
                and int(evidence.get("unique_jobs", 0)) >= 2
                and cls._valid_sha256(digest)
                and Decimal("0") <= settled < released_stage <= hard_limit
                and packet.get("model") == "gpt-5.3-codex"
                and packet.get("reasoning") in {"low", "medium"}
            ):
                return sha256_value(
                    {
                        "cursor_evidence_sha256": str(digest),
                        "settled_usd": format(settled, "f"),
                        "released_stage_usd": format(released_stage, "f"),
                        "hard_limit_usd": format(hard_limit, "f"),
                        "model": packet.get("model"),
                        "reasoning": packet.get("reasoning"),
                    }
                )
        return None

    def _discover_provider_work_batch(
        self,
        snapshot: dict[str, Any],
        moment: datetime,
        candidates_override: list[Path] | None = None,
    ) -> list[tuple[ReadyWorkUnit, RouteDecision, dict[str, Any]]]:
        root_value = self.config.provider_work_root
        if root_value is None or not root_value.exists():
            return []
        root = root_value.resolve(strict=True)
        if candidates_override is None:
            candidates, scan_capped = _bounded_json_scan(
                root,
                limit=MAX_PROVIDER_WORK_SCAN_UNITS,
            )
            if scan_capped:
                raise RuntimeError("RUNTIME_INVENTORY_PROVIDER_WORK_SCAN_BOUND_EXCEEDED")
        else:
            candidates = candidates_override
        if len(candidates) > MAX_PROVIDER_WORK_SCAN_UNITS:
            raise RuntimeError("RUNTIME_INVENTORY_PROVIDER_WORK_SCAN_BOUND_EXCEEDED")
        candidate_records: list[tuple[Path, bytes, str, bool]] = []
        content_address_work_units: dict[str, set[str]] = {}
        for source in candidates:
            resolved = source.resolve(strict=True)
            if root not in resolved.parents:
                raise RuntimeError("RUNTIME_INVENTORY_PROVIDER_WORK_OUTSIDE_ALLOWLIST")
            if not 0 < resolved.stat().st_size <= MAX_PROVIDER_WORK_BYTES:
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_PACKET_SIZE_INVALID")
            raw = resolved.read_bytes()
            source_sha256 = hashlib.sha256(raw).hexdigest()
            content_addressed = self._valid_sha256(resolved.stem)
            if content_addressed and resolved.stem != source_sha256:
                raise RuntimeError("RUNTIME_INVENTORY_PROVIDER_WORK_CONTENT_ADDRESS_MISMATCH")
            if content_addressed:
                content_address_work_units[source_sha256] = {
                    prefix + source_sha256[:20] for prefix in DYNAMIC_PREFIXES
                }
            candidate_records.append((resolved, raw, source_sha256, content_addressed))

        content_address_states = self.state.work_unit_states(
            {
                work_unit_id
                for work_unit_ids in content_address_work_units.values()
                for work_unit_id in work_unit_ids
            }
        )
        terminal_content_addresses = {
            digest
            for digest, work_unit_ids in content_address_work_units.items()
            if any(
                content_address_states.get(work_unit_id) in TERMINAL_STATES
                for work_unit_id in work_unit_ids
            )
        }
        ready_jira_units = {
            str(record["jira_key"])
            for _path, record, _digest in self._jira_ready_records(limit=MAX_PROVIDER_WORK_UNITS)
        }
        discovered: list[tuple[ReadyWorkUnit, RouteDecision, dict[str, Any]]] = []
        for resolved, raw, source_sha256, content_addressed in candidate_records:
            if content_addressed and source_sha256 in terminal_content_addresses:
                continue
            packet = json.loads(raw)
            if not isinstance(packet, dict) or packet.get("schema_version") != 1:
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_PACKET_INVALID")
            if packet.get("authority") != "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES":
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_PACKET_AUTHORITY_INVALID")
            provider = packet.get("provider")
            task_format = packet.get("task_format")
            openrouter_identity_hashes: dict[str, str] | None = None
            if provider == "openai_direct" and task_format == "governed_openai_candidate_v1":
                prefix = "AUTO-OAI-"
                disposition = RoutingDisposition.DIRECT_OPENAI
                model = packet.get("job", {}).get("model")
            elif provider == "openrouter" and task_format == OPENROUTER_TASK_FORMAT:
                task_id = packet.get("task_id")
                authority = packet.get("authority")
                prompt_version = packet.get("prompt_version")
                request_schema_version = packet.get("request_schema_version")
                provider_policy_version = packet.get("provider_policy_version")
                reasoning_effort = packet.get("reasoning_effort")
                max_output_tokens = packet.get("max_output_tokens")
                base_commit = packet.get("base_commit")
                evidence_excerpts = packet.get("evidence_excerpts")
                openrouter_identity_hashes = packet.get("identity_hashes")
                expected_base_commit = self._snapshot_release_commit(snapshot)
                if (
                    not isinstance(task_id, str)
                    or not task_id
                    or not isinstance(authority, str)
                    or not authority
                    or not isinstance(prompt_version, str)
                    or not prompt_version
                    or not isinstance(request_schema_version, str)
                    or not request_schema_version
                    or not isinstance(provider_policy_version, str)
                    or not provider_policy_version
                    or not isinstance(reasoning_effort, str)
                    or not reasoning_effort
                    or not isinstance(max_output_tokens, int)
                    or max_output_tokens <= 0
                    or not isinstance(base_commit, str)
                    or len(base_commit) != 40
                    or any(character not in "0123456789abcdef" for character in base_commit)
                    or base_commit != expected_base_commit
                    or not isinstance(evidence_excerpts, list)
                    or not evidence_excerpts
                    or any(not isinstance(item, str) or not item for item in evidence_excerpts)
                    or not isinstance(openrouter_identity_hashes, dict)
                ):
                    raise ValueError("RUNTIME_INVENTORY_OPENROUTER_PACKET_INVALID")
                required_hashes = {
                    "task_sha256",
                    "schema_sha256",
                    "policy_sha256",
                    "model_sha256",
                    "reasoning_sha256",
                    "source_sha256",
                }
                if set(openrouter_identity_hashes) != required_hashes or not all(
                    self._valid_sha256(openrouter_identity_hashes[key]) for key in required_hashes
                ):
                    raise ValueError("RUNTIME_INVENTORY_OPENROUTER_PACKET_HASHES_INVALID")
                prefix = "AUTO-OR-"
                disposition = RoutingDisposition.OPENROUTER
                model = packet.get("model")
            elif provider == "ollama_local" and task_format == "embedding_dedup_semantic_candidate_retrieval":
                prefix = "AUTO-BGE-"
                disposition = RoutingDisposition.LOCAL_QWEN
                model = packet.get("model")
            elif provider == "cursor" and task_format in CURSOR_TASK_FORMATS:
                expected_base_commit = self._snapshot_release_commit(snapshot)
                implementation = task_format == CURSOR_IMPLEMENTATION_TASK_FORMAT
                expected_schema = (
                    CURSOR_IMPLEMENTATION_SCHEMA_SHA256
                    if implementation
                    else CURSOR_SCHEMA_SHA256
                )
                if (
                    packet.get("jira_unit") != "POST-SUBTASK-202"
                    or packet.get("schema_sha256") != expected_schema
                    or packet.get("model") != "gpt-5.3-codex"
                    or packet.get("reasoning") not in {"low", "medium"}
                    or packet.get("base_commit") != expected_base_commit
                    or packet.get("starting_ref") != expected_base_commit
                    or packet.get("fast") is not False
                    or packet.get("work_on_current_branch") is not False
                    or packet.get("auto_create_pr") is not False
                    or not isinstance(packet.get("repository_url"), str)
                    or not str(packet.get("repository_url")).startswith("https://github.com/")
                    or not isinstance(packet.get("prompt"), str)
                    or not str(packet.get("prompt")).strip()
                    or Decimal(str(packet.get("max_reservation_usd", "0"))) <= 0
                ):
                    raise ValueError("RUNTIME_INVENTORY_CURSOR_PACKET_INVALID")
                if implementation:
                    allowed_paths = packet.get("allowed_paths")
                    required_tests = packet.get("required_tests")
                    if (
                        not isinstance(packet.get("source_jira_unit"), str)
                        or not isinstance(packet.get("source_review_work_unit_id"), str)
                        or not self._valid_sha256(packet.get("source_review_result_sha256"))
                        or not self._valid_sha256(
                            packet.get("source_review_disposition_sha256")
                        )
                        or not isinstance(allowed_paths, list)
                        or not allowed_paths
                        or any(not _safe_cursor_repository_path(path) for path in allowed_paths)
                        or not isinstance(required_tests, list)
                        or any(
                            not isinstance(path, str) or not path
                            for path in required_tests
                        )
                    ):
                        raise ValueError(
                            "RUNTIME_INVENTORY_CURSOR_IMPLEMENTATION_PACKET_INVALID"
                        )
                prefix = "AUTO-CURSOR-"
                disposition = RoutingDisposition.CURSOR
                model = packet.get("model")
            elif provider == "remote_cpu_worker" and str(packet.get("task", "")) in CPU_EXACT_ROUTES:
                task = str(packet["task"])
                expected_format, expected_schema, prefix = CPU_EXACT_ROUTES[task]
                payload = packet.get("payload")
                payload_shape_valid = (
                    task == "CANONICAL_JSON"
                    and isinstance(payload, dict)
                    and set(payload) == {"value"}
                ) or (
                    task == "LINE_HASH_MANIFEST"
                    and isinstance(payload, dict)
                    and set(payload) == {"lines"}
                    and isinstance(payload["lines"], list)
                    and bool(payload["lines"])
                    and len(payload["lines"]) <= MAX_RECORDS
                    and all(isinstance(item, str) for item in payload["lines"])
                ) or (
                    task == "EXACT_TEXT_DEDUP"
                    and isinstance(payload, dict)
                    and set(payload) == {"records"}
                    and isinstance(payload["records"], list)
                    and bool(payload["records"])
                    and len(payload["records"]) <= MAX_RECORDS
                    and all(
                        isinstance(item, dict)
                        and set(item) == {"id", "text"}
                        and isinstance(item["id"], str)
                        and bool(item["id"])
                        and isinstance(item["text"], str)
                        for item in payload["records"]
                    )
                    and len({item["id"] for item in payload["records"]})
                    == len(payload["records"])
                )
                if (
                    task_format != expected_format
                    or packet.get("schema_sha256") != expected_schema
                    or not payload_shape_valid
                ):
                    raise ValueError("RUNTIME_INVENTORY_CPU_PROVIDER_PACKET_INVALID")
                disposition = RoutingDisposition.REMOTE_CPU_WORKER
                model = "DETERMINISTIC_CPU_WORKER_V2"
            else:
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_PACKET_ROUTE_INVALID")
            readiness = self._provider_readiness(snapshot, packet)
            if readiness is None:
                raise RuntimeError("RUNTIME_INVENTORY_PROVIDER_EXACT_ROUTE_NOT_READY")
            control_jira_unit = str(packet.get("jira_unit", ""))
            jira_unit = str(packet.get("source_jira_unit") or control_jira_unit)
            schema_sha256 = str(packet.get("schema_sha256", ""))
            if not control_jira_unit or not jira_unit or not self._valid_sha256(schema_sha256):
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_PACKET_IDENTITY_INVALID")
            if packet.get("source_jira_unit") is not None and jira_unit not in ready_jira_units:
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_SOURCE_JIRA_NOT_READY")
            source_hashes = packet.get("source_hashes", [])
            if not isinstance(source_hashes, list) or not source_hashes or not all(self._valid_sha256(item) for item in source_hashes):
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_SOURCE_HASHES_INVALID")
            if provider == "openrouter":
                assert openrouter_identity_hashes is not None
                expected_hashes = {
                    "task_sha256": sha256_value(
                        {
                            "task_id": packet["task_id"],
                            "jira_unit": control_jira_unit,
                            "authority": packet["authority"],
                        }
                    ),
                    "schema_sha256": sha256_value(
                        {
                            "schema_version": packet["request_schema_version"],
                            "schema_sha256": schema_sha256,
                        }
                    ),
                    "policy_sha256": sha256_value(
                        {
                            "provider_policy_version": packet["provider_policy_version"],
                            "task_format": task_format,
                        }
                    ),
                    "model_sha256": sha256_value({"model": packet.get("model")}),
                    "reasoning_sha256": sha256_value(
                        {
                            "reasoning_effort": packet["reasoning_effort"],
                            "max_output_tokens": packet["max_output_tokens"],
                        }
                    ),
                    "source_sha256": sha256_value(tuple(source_hashes)),
                }
                if openrouter_identity_hashes != expected_hashes:
                    raise ValueError("RUNTIME_INVENTORY_OPENROUTER_IDENTITY_HASH_MISMATCH")
            packet_path, packet_sha256 = _content_addressed_json(self.config.packet_root, "provider-packets", packet)
            work_unit_id = prefix + packet_sha256[:20]
            unit = ReadyWorkUnit(
                work_unit_id=work_unit_id,
                jira_unit=jira_unit,
                task_format=str(task_format),
                schema_sha256=schema_sha256,
                authority="CANDIDATE_ONLY",
                source_hashes=tuple([*source_hashes, source_sha256, packet_sha256]),
                dependencies=tuple(packet.get("dependencies", [])),
                pre_routing_effort_points=int(packet.get("pre_routing_effort_points", 1)),
                scope=str(packet.get("scope", "Governed granular candidate-only provider work")),
            )
            decision = RouteDecision(
                work_unit_id=work_unit_id,
                work_unit_identity=unit.identity(),
                disposition=disposition,
                provider=str(provider),
                model=str(model),
                reason="EXACT_ROUTE_READY_AND_GRANULAR_PACKET_MATERIALIZED",
                decided_at=rfc3339(moment),
            )
            discovered.append((unit, decision, {
                "packet_path": str(packet_path), "packet_sha256": packet_sha256,
                "readiness_evidence_sha256": readiness,
            }))
        states = self.state.work_unit_states({unit.work_unit_id for unit, _, _ in discovered})
        active = [
            entry
            for entry in discovered
            if states.get(entry[0].work_unit_id) not in TERMINAL_STATES
        ]
        if len(active) > MAX_PROVIDER_WORK_UNITS:
            raise RuntimeError("RUNTIME_INVENTORY_PROVIDER_WORK_ACTIVE_BOUND_EXCEEDED")
        return active

    def _discover_provider_work(
        self, snapshot: dict[str, Any], moment: datetime
    ) -> list[tuple[ReadyWorkUnit, RouteDecision, dict[str, Any]]]:
        """Isolate malformed packets by exact identity while admitting unrelated work."""
        self._provider_packet_findings = []
        root_value = self.config.provider_work_root
        if root_value is None or not root_value.exists():
            return []
        root = root_value.resolve(strict=True)
        candidates, scan_capped, visited_files = _bounded_distinct_json_scan(
            root,
            limit=MAX_PROVIDER_WORK_SCAN_UNITS,
            file_visit_limit=MAX_PROVIDER_WORK_FILE_VISITS,
        )
        if scan_capped:
            finding = {
                "finding": "RUNTIME_INVENTORY_PROVIDER_WORK_SCAN_CAPACITY_DEFERRED",
                "observed_at": rfc3339(moment),
                "disposition": "EXCESS_PACKETS_REMAIN_QUEUED_UNRELATED_PACKETS_CONTINUE",
                "visited_files": visited_files,
                "distinct_candidates": len(candidates),
            }
            self._provider_packet_findings.append(finding)
            self.state.append_event("PROVIDER_PACKET_CAPACITY_DEFERRED", finding, now=moment)
        discovered_by_work_unit: dict[
            str, tuple[ReadyWorkUnit, RouteDecision, dict[str, Any]]
        ] = {}
        for source in candidates:
            try:
                if not 0 < source.stat().st_size <= MAX_PROVIDER_WORK_BYTES:
                    raise ValueError("RUNTIME_INVENTORY_PROVIDER_PACKET_SIZE_INVALID")
                for entry in self._discover_provider_work_batch(
                    snapshot,
                    moment,
                    candidates_override=[source],
                ):
                    discovered_by_work_unit.setdefault(entry[0].work_unit_id, entry)
            except (OSError, KeyError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                try:
                    raw = source.read_bytes()
                except OSError:
                    raw = str(source).encode("utf-8")
                digest = hashlib.sha256(raw).hexdigest()
                quarantine_root = root.parent / "quarantine" / "sha256" / digest
                payload_path = quarantine_root / "packet.json"
                finding_path = quarantine_root / "finding.json"
                if not payload_path.exists():
                    _atomic_write(payload_path, raw)
                elif payload_path.read_bytes() != raw:
                    raise RuntimeError("PROVIDER_PACKET_QUARANTINE_COLLISION")
                finding = {
                    "finding": type(exc).__name__ + ":" + str(exc)[:240],
                    "observed_at": rfc3339(moment),
                    "disposition": "PACKET_QUARANTINED_UNRELATED_PROVIDER_WORK_CONTINUES",
                    "packet_sha256": digest,
                    "source_relative_path": source.relative_to(root).as_posix(),
                    "quarantine_path": str(payload_path),
                }
                try:
                    packet = json.loads(raw)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    packet = None
                if isinstance(packet, dict):
                    canonical_packet_sha256 = hashlib.sha256(
                        canonical_json_bytes(packet) + b"\n"
                    ).hexdigest()
                    work_unit_id = _dynamic_work_unit_id(packet, canonical_packet_sha256)
                    if work_unit_id is not None:
                        finding["work_unit_id"] = work_unit_id
                        state = self.state.work_unit_states({work_unit_id}).get(work_unit_id)
                        if state == "DISCOVERED":
                            try:
                                self.state.transition(
                                    work_unit_id=work_unit_id,
                                    expected_state="DISCOVERED",
                                    new_state="QUARANTINED",
                                    reason="PROVIDER_PACKET_QUARANTINED_BEFORE_ADMISSION",
                                    actor="runtime_inventory",
                                    evidence_sha256=digest,
                                    now=moment,
                                )
                                finding["work_unit_state_disposition"] = "QUARANTINED"
                            except RuntimeError as transition_error:
                                current_state = self.state.work_unit_states({work_unit_id}).get(
                                    work_unit_id
                                )
                                finding["work_unit_state_disposition"] = (
                                    f"PRESERVED_CONCURRENT_STATE:{current_state}"
                                )
                                finding["state_transition_finding"] = str(transition_error)[:160]
                        elif state is not None:
                            finding["work_unit_state_disposition"] = (
                                f"PRESERVED_EXISTING_STATE:{state}"
                            )
                finding_data = canonical_json_bytes(finding) + b"\n"
                if not finding_path.exists():
                    _atomic_write(finding_path, finding_data)
                elif finding_path.read_bytes() != finding_data:
                    versioned = quarantine_root / f"finding-{hashlib.sha256(finding_data).hexdigest()}.json"
                    if not versioned.exists():
                        _atomic_write(versioned, finding_data)
                try:
                    source.unlink()
                except OSError:
                    finding["disposition"] = "PACKET_QUARANTINED_SOURCE_REMOVAL_PENDING"
                self._provider_packet_findings.append(finding)
                self.state.append_event("PROVIDER_PACKET_QUARANTINED", finding, now=moment)
        discovered = list(discovered_by_work_unit.values())
        if len(discovered) > MAX_PROVIDER_WORK_UNITS:
            finding = {
                "finding": "RUNTIME_INVENTORY_PROVIDER_WORK_ACTIVE_CAPACITY_DEFERRED",
                "observed_at": rfc3339(moment),
                "disposition": "DISTINCT_EXCESS_PACKETS_REMAIN_QUEUED_DUPLICATES_DO_NOT_CONSUME_CAPACITY",
                "distinct_active_units": len(discovered),
                "admitted_units": MAX_PROVIDER_WORK_UNITS,
            }
            self._provider_packet_findings.append(finding)
            self.state.append_event("PROVIDER_PACKET_CAPACITY_DEFERRED", finding, now=moment)
            discovered = discovered[:MAX_PROVIDER_WORK_UNITS]
        return discovered

    @staticmethod
    def _cpu_qualified(snapshot: dict[str, Any]) -> bool:
        return cpu_qualification_evidence_sha256(snapshot) is not None

    def _operational_demand(
        self,
        snapshot: dict[str, Any],
        route_decisions: list[dict[str, Any]],
        work_unit_roles: dict[str, str],
    ) -> dict[str, Any]:
        """Compute campaign debt independently of the currently materialized packet queue."""
        policy_path = self.config.semantic_policy_path
        if policy_path is None:
            return {"enabled": False, "providers": {}, "unmet_provider_count": 0}
        policy = _verified_json(policy_path)
        minimums = policy.get("execution_minimums", {})
        external = snapshot.get("external_evidence", {})
        controller = self.state.provider_run_summary(current_release_only=False)
        current_release = self.state.provider_run_summary(current_release_only=True)
        provider_map = {
            "cursor": ("cursor", "cursor"),
            "openrouter": ("openrouter", "openrouter"),
            "direct_openai": ("openai_direct", "openai"),
            "remote_cpu_worker": ("remote_cpu_worker", "cpu_worker"),
            "local_models_post_qualification": ("ollama_local", "local_qwen"),
        }
        active_packets: dict[str, int] = {}
        atomic_ids = {
            str(decision.get("work_unit_id", ""))
            for decision in route_decisions
            if work_unit_roles.get(str(decision.get("work_unit_id", ""))) == ATOMIC_EXECUTABLE
        }
        durable_states = self.state.work_unit_states(atomic_ids)
        for decision in route_decisions:
            provider = decision.get("provider")
            work_unit_id = str(decision.get("work_unit_id", ""))
            if (
                provider
                and decision.get("disposition") in {
                    RoutingDisposition.DIRECT_OPENAI.value,
                    RoutingDisposition.OPENROUTER.value,
                    RoutingDisposition.CURSOR.value,
                    RoutingDisposition.LOCAL_QWEN.value,
                    RoutingDisposition.REMOTE_CPU_WORKER.value,
                }
                and work_unit_roles.get(work_unit_id) == ATOMIC_EXECUTABLE
                and durable_states.get(work_unit_id) not in TERMINAL_STATES
            ):
                active_packets[str(provider)] = active_packets.get(str(provider), 0) + 1

        providers: dict[str, Any] = {}
        for policy_key, (provider, evidence_key) in provider_map.items():
            requirement = minimums.get(policy_key)
            if not isinstance(requirement, dict):
                continue
            required_units = int(requirement.get("new_controller_routed_units", requirement.get("units", 0)))
            required_effort = int(requirement.get("effort_points", 0))
            required_accepted = int(requirement.get("accepted_useful", 0))
            summary = controller.get(provider, {})
            observed_units = int(summary.get("closed_runs", 0))
            observed_effort = int(summary.get("closed_effort_points", 0))
            useful = summary.get("useful_work", {})
            observed_accepted = int(useful.get("accepted_useful_outputs", 0))
            release_summary = current_release.get(provider, {})
            pending_review = int(
                release_summary.get(
                    "pending_downstream_review",
                    release_summary.get("review_dispositions", {}).get("REVIEW_ONLY", 0),
                )
            )
            semantic = external.get(evidence_key, {})
            manual_or_external_units = int(
                semantic.get("unique_jobs", semantic.get("requests", semantic.get("settled_calls", 0)))
            )
            controller_routed_units = int(summary.get("closed_runs", 0))
            deficits = {
                "units": max(0, required_units - observed_units),
                "effort_points": max(0, required_effort - observed_effort),
                "accepted_useful": max(0, required_accepted - observed_accepted),
            }
            unmet = any(deficits.values())
            useful_work_gate_failed = (
                required_accepted > 0
                and deficits["accepted_useful"] > 0
                and deficits["units"] == 0
                and deficits["effort_points"] == 0
                and active_packets.get(provider, 0) == 0
                and pending_review == 0
            )
            admission_suspended = (
                useful_work_gate_failed
                and provider in USEFUL_WORK_SATURATION_SUSPEND_PROVIDERS
            )
            if required_accepted == 0:
                useful_work_gate_state = "NOT_APPLICABLE"
            elif deficits["accepted_useful"] == 0:
                useful_work_gate_state = "PASS"
            elif useful_work_gate_failed:
                useful_work_gate_state = "FAILED_SATURATED_BELOW_ACCEPTANCE_TARGET"
            else:
                useful_work_gate_state = "EVALUATION_ACTIVE"
            providers[provider] = {
                "policy_key": policy_key,
                "required_units": required_units,
                "required_effort_points": required_effort,
                "required_accepted_useful": required_accepted,
                "observed_units": observed_units,
                "observed_effort_points": observed_effort,
                "observed_accepted_useful": observed_accepted,
                "controller_routed_units": controller_routed_units,
                "current_release_closed_units": int(release_summary.get("closed_runs", 0)),
                "current_release_effort_points": int(
                    release_summary.get("closed_effort_points", 0)
                ),
                "manual_or_external_units": manual_or_external_units,
                "active_execution_packets": active_packets.get(provider, 0),
                "pending_review_results": pending_review,
                "deficits": deficits,
                "unmet": unmet,
                "admission_suspended": admission_suspended,
                "useful_work_remediation": (
                    "SUSPEND_EXACT_ROUTE"
                    if admission_suspended
                    else "CONTINUE_ADMISSION_AND_REMEDIATE_DOWNSTREAM_CONSUMPTION"
                    if useful_work_gate_failed
                    else None
                ),
                "useful_work_gate_state": useful_work_gate_state,
            }
        return {
            "enabled": True,
            "providers": providers,
            "unmet_provider_count": sum(int(item["unmet"]) for item in providers.values()),
            "unmet_without_packets": sorted(
                provider
                for provider, item in providers.items()
                if item["unmet"]
                and item["active_execution_packets"] == 0
                and item["pending_review_results"] == 0
                and not item["admission_suspended"]
            ),
            "unmet_pending_review": sorted(
                provider
                for provider, item in providers.items()
                if item["unmet"]
                and item["active_execution_packets"] == 0
                and item["pending_review_results"] > 0
            ),
            "empirically_suspended": sorted(
                provider
                for provider, item in providers.items()
                if item["admission_suspended"]
            ),
        }

    def _materialize_continuous_openrouter_work(
        self,
        snapshot: dict[str, Any],
        demand: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Compile new real BAS evidence into three governed reasoning categories."""
        queue_root = self.config.provider_work_root
        manifests_root = self.config.manifests_root.resolve(strict=False)
        if queue_root is None or not manifests_root.is_dir():
            return []
        openrouter = demand.get("providers", {}).get("openrouter", {})
        if (
            not openrouter.get("unmet")
            or openrouter.get("admission_suspended")
            or int(openrouter.get("active_execution_packets", 0)) > 0
            or int(openrouter.get("pending_review_results", 0)) >= 6
        ):
            return []
        routes = snapshot.get("external_evidence", {}).get("openrouter", {}).get("routes", [])
        ready_routes = {
            str(route["task_id"]): route
            for route in routes
            if isinstance(route, dict)
            and route.get("task_id") in {
                "patch_candidate", "schema_drift_review", "reconciliation_ranking", "independent_review"
            }
            and route.get("readiness_supported_state") == "READY"
            and route.get("evidence_verified") is True
        }
        if not ready_routes:
            return []
        release_commit = self._snapshot_release_commit(snapshot)
        capacity = max(0, 6 - int(openrouter.get("pending_review_results", 0)))
        created: list[dict[str, str]] = []
        jira_route = ready_routes.get("independent_review")
        if jira_route is not None and capacity > 0 and self.config.project_root is not None:
            project_root = self.config.project_root.resolve(strict=True)
            for source, record, source_sha256 in self._jira_ready_records(limit=4):
                relative = source.relative_to(project_root).as_posix()
                evidence = json.dumps(
                    {
                        "instruction": (
                            "Independently review the bounded implementation contract and declared allowed paths. "
                            "Return evidence-backed findings, unsupported claims, and recommended checks; do not claim completion."
                        ),
                        "jira_key": record["jira_key"],
                        "local_id": record["local_id"],
                        "objective": record.get("objective"),
                        "scope": record.get("scope"),
                        "allowed_modification_paths": record.get("allowed_modification_paths", []),
                        "files_expected_to_be_touched": record.get("files_expected_to_be_touched", []),
                        "files_to_inspect": record.get("files_to_inspect", []),
                        "acceptance_criteria": record.get("acceptance_criteria", []),
                        "required_tests": record.get("required_tests", []),
                        "source_relative_path": relative,
                        "source_sha256": source_sha256,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                if len(evidence) > 12000:
                    continue
                control_jira_unit = self._openrouter_jira_identity("independent_review")
                packet: dict[str, Any] = {
                    "schema_version": 1,
                    "provider": "openrouter",
                    "task_format": OPENROUTER_TASK_FORMAT,
                    "task_id": "independent_review",
                    "jira_unit": control_jira_unit,
                    "source_jira_unit": str(record["jira_key"]),
                    "schema_sha256": str(jira_route["schema_sha256"]),
                    "request_schema_version": str(jira_route["request_schema_version"]),
                    "provider_policy_version": str(jira_route["provider_policy_version"]),
                    "model": str(jira_route["model"]),
                    "reasoning_effort": str(jira_route["reasoning_effort"]),
                    "max_output_tokens": 900,
                    "base_commit": release_commit,
                    "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
                    "source_hashes": [source_sha256],
                    "dependencies": list(record.get("dependencies", [])),
                    "pre_routing_effort_points": 5,
                    "scope": f"Jira-derived independent candidate implementation review for {record['jira_key']}",
                    "prompt_version": "continuous-jira-ready-independent-review-v1",
                    "evidence_excerpts": [evidence],
                }
                packet["identity_hashes"] = {
                    "task_sha256": sha256_value(
                        {
                            "task_id": packet["task_id"],
                            "jira_unit": control_jira_unit,
                            "authority": packet["authority"],
                        }
                    ),
                    "schema_sha256": sha256_value(
                        {
                            "schema_version": packet["request_schema_version"],
                            "schema_sha256": packet["schema_sha256"],
                        }
                    ),
                    "policy_sha256": sha256_value(
                        {
                            "provider_policy_version": packet["provider_policy_version"],
                            "task_format": packet["task_format"],
                        }
                    ),
                    "model_sha256": sha256_value({"model": packet["model"]}),
                    "reasoning_sha256": sha256_value(
                        {
                            "reasoning_effort": packet["reasoning_effort"],
                            "max_output_tokens": packet["max_output_tokens"],
                        }
                    ),
                    "source_sha256": sha256_value(tuple(packet["source_hashes"])),
                }
                data = canonical_json_bytes(packet) + b"\n"
                digest = hashlib.sha256(data).hexdigest()
                work_unit_id = "AUTO-OR-" + digest[:20]
                if self.state.work_unit_states({work_unit_id}).get(work_unit_id) in TERMINAL_STATES:
                    continue
                destination = queue_root / "continuous" / "sha256" / digest[:2] / f"{digest}.json"
                if destination.exists() and destination.read_bytes() != data:
                    raise RuntimeError("CONTINUOUS_JIRA_OPENROUTER_PACKET_COLLISION")
                if not destination.exists():
                    _atomic_write(destination, data)
                created.append(
                    {
                        "provider": "openrouter",
                        "task_id": "independent_review",
                        "source_relative_path": relative,
                        "source_sha256": source_sha256,
                        "packet_path": str(destination),
                        "packet_sha256": digest,
                    }
                )
                break
        data_root = manifests_root.parent
        source_specs = (
            (
                "schema_drift_review",
                manifests_root,
                None,
                "Identify only evidence-supported schema drift, missingness, reconciliation, or provenance risks.",
            ),
            (
                "reconciliation_ranking",
                data_root / "reconciliation" / "historical_expansion",
                None,
                "Rank the evidence-supported reconciliation or missingness risks requiring deterministic follow-up.",
            ),
            (
                "independent_review",
                data_root / "reconciliation" / "feature_engineering",
                None,
                "Independently challenge this candidate artifact for leakage, unsupported claims, and missing evidence.",
            ),
        )
        for task_id, task_root, allowed_names, instruction in source_specs:
            if task_id not in ready_routes or not task_root.is_dir():
                continue
            if task_root == manifests_root:
                scanned, _ = _bounded_top_level_json_scan(
                    task_root,
                    limit=MAX_HISTORICAL_MANIFEST_SCAN_UNITS,
                    name_prefix="snap_",
                )
            else:
                scanned, _ = _bounded_json_scan(
                    task_root,
                    limit=256,
                    allowed_names=allowed_names,
                )
            candidates = sorted(
                (
                    path for path in scanned
                    if task_root != manifests_root or path.name.startswith("snap_")
                    if 0 < path.stat().st_size <= MAX_DISCOVERED_MANIFEST_BYTES
                ),
                key=lambda path: (-path.stat().st_mtime_ns, path.as_posix()),
            )
            route = ready_routes[task_id]
            for resolved in candidates:
                if len(created) >= min(3, capacity):
                    break
                raw = resolved.read_bytes()
                source_sha256 = hashlib.sha256(raw).hexdigest()
                value = json.loads(raw)
                if not isinstance(value, dict):
                    continue
                relative = resolved.relative_to(data_root.resolve(strict=True)).as_posix()
                evidence = json.dumps(
                    {
                        "instruction": instruction + " Use NOT_PRESENT when evidence is absent.",
                        "source_relative_path": relative,
                        "source_sha256": source_sha256,
                        "evidence": value,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                if task_id == "reconciliation_ranking":
                    reconciliation = value.get("reconciliation")
                    reason_counts = (
                        reconciliation.get("unresolved_reason_counts")
                        if isinstance(reconciliation, dict)
                        else value.get("unresolved_reason_counts")
                    )
                    if not isinstance(reason_counts, dict) or not reason_counts:
                        continue
                    candidate_ids = sorted(
                        str(candidate_id)
                        for candidate_id in reason_counts
                        if str(candidate_id)
                    )
                    if not candidate_ids:
                        continue
                    evidence_value = json.loads(evidence)
                    evidence_value["reconciliation_candidate_binding_v1"] = {
                        "candidate_ids": candidate_ids
                    }
                    evidence_value["instruction"] += (
                        " candidate_ids must be selected only from the supplied binding."
                    )
                    evidence = json.dumps(
                        evidence_value,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                if len(evidence) > 12000:
                    continue
                source_hashes = [source_sha256]
                packet: dict[str, Any] = {
                    "schema_version": 1,
                    "provider": "openrouter",
                    "task_format": OPENROUTER_TASK_FORMAT,
                    "task_id": task_id,
                    "jira_unit": self._openrouter_jira_identity(task_id),
                    "schema_sha256": str(route["schema_sha256"]),
                    "request_schema_version": str(route["request_schema_version"]),
                    "provider_policy_version": str(route["provider_policy_version"]),
                    "model": str(route["model"]),
                    "reasoning_effort": str(route["reasoning_effort"]),
                    "max_output_tokens": 512,
                    "base_commit": release_commit,
                    "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
                    "source_hashes": source_hashes,
                    "dependencies": [],
                    "pre_routing_effort_points": 3,
                    "scope": f"Continuous candidate-only {task_id} for {relative}",
                    "prompt_version": "continuous-real-bas-evidence-v2",
                    "evidence_excerpts": [evidence],
                }
                packet["identity_hashes"] = {
                    "task_sha256": sha256_value(
                        {"task_id": task_id, "jira_unit": packet["jira_unit"], "authority": packet["authority"]}
                    ),
                    "schema_sha256": sha256_value(
                        {"schema_version": packet["request_schema_version"], "schema_sha256": packet["schema_sha256"]}
                    ),
                    "policy_sha256": sha256_value(
                        {"provider_policy_version": packet["provider_policy_version"], "task_format": packet["task_format"]}
                    ),
                    "model_sha256": sha256_value({"model": packet["model"]}),
                    "reasoning_sha256": sha256_value(
                        {"reasoning_effort": packet["reasoning_effort"], "max_output_tokens": packet["max_output_tokens"]}
                    ),
                    "source_sha256": sha256_value(tuple(source_hashes)),
                }
                data = canonical_json_bytes(packet) + b"\n"
                digest = hashlib.sha256(data).hexdigest()
                work_unit_id = "AUTO-OR-" + digest[:20]
                if self.state.work_unit_states({work_unit_id}).get(work_unit_id) in TERMINAL_STATES:
                    continue
                destination = queue_root / "continuous" / "sha256" / digest[:2] / f"{digest}.json"
                if destination.exists() and destination.read_bytes() != data:
                    raise RuntimeError("CONTINUOUS_WORK_PACKET_COLLISION")
                if not destination.exists():
                    _atomic_write(destination, data)
                created.append(
                    {
                        "provider": "openrouter",
                        "task_id": task_id,
                        "source_relative_path": relative,
                        "source_sha256": source_sha256,
                        "packet_path": str(destination),
                        "packet_sha256": digest,
                    }
                )
                break
            if len(created) >= min(3, capacity):
                break
        return created

    def _materialize_continuous_cursor_work(
        self,
        snapshot: dict[str, Any],
        demand: dict[str, Any],
    ) -> list[dict[str, str]]:
        queue_root = self.config.provider_work_root
        if queue_root is None:
            return []
        cursor = demand.get("providers", {}).get("cursor", {})
        if (
            not cursor.get("unmet")
            or cursor.get("admission_suspended")
            or int(cursor.get("active_execution_packets", 0)) > 0
            or int(cursor.get("pending_review_results", 0)) > 0
        ):
            return []
        release_commit = self._snapshot_release_commit(snapshot)
        release_root = self.config.release_root
        if release_root is None:
            return []
        created = self._materialize_cursor_implementation_work(
            snapshot=snapshot,
            release_commit=release_commit,
            limit=1,
        )
        # A reviewed implementation candidate is the only Cursor work that can
        # directly produce a consumable repository artifact.  Do not spend the
        # second concurrency/budget slot on another read-only review while an
        # implementation packet is ready; that behavior previously exhausted
        # the released stage while leaving useful offload at zero.
        if created:
            return created
        review_targets: list[tuple[Path, str, str | None, str | None]] = []
        if self.config.project_root is not None:
            project_root = self.config.project_root.resolve(strict=True)
            for source, record, _source_sha256 in self._jira_ready_records(limit=8):
                relative = source.relative_to(project_root).as_posix()
                compact_contract = json.dumps(
                    {
                        "jira_key": record["jira_key"],
                        "local_id": record["local_id"],
                        "objective": record.get("objective"),
                        "scope": record.get("scope"),
                        "allowed_modification_paths": record.get("allowed_modification_paths", []),
                        "files_expected_to_be_touched": record.get("files_expected_to_be_touched", []),
                        "files_to_inspect": record.get("files_to_inspect", []),
                        "acceptance_criteria": record.get("acceptance_criteria", []),
                        "required_tests": record.get("required_tests", []),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                if len(compact_contract) > 14000:
                    continue
                focus = (
                    f"Evaluate the executable Jira contract below against exact current main. Identify the "
                    f"smallest valid implementation, exact allowed paths, existing reusable code, required tests, "
                    f"and any evidence-backed blocker. Jira contract: {compact_contract}"
                )
                review_targets.append((source, focus, str(record["jira_key"]), relative))
        fixed_review_targets = (
            ("src/aggie_analytics/assistive_plane/inventory_runtime.py", "bounded semantic work discovery, duplicate suppression, and per-packet isolation"),
            ("src/aggie_analytics/assistive_plane/scheduler_runtime.py", "durable provider lifecycle, restart recovery, and no duplicate submission"),
            ("src/aggie_analytics/assistive_plane/controller_state.py", "atomic state transitions, leases, settlements, and reconciliation"),
            ("src/aggie_analytics/assistive_plane/watchdog.py", "independent operational completeness and starvation detection"),
            ("src/aggie_analytics/assistive_plane/provider_adapters.py", "exact route identity, candidate-only authority, and usage settlement"),
            ("src/aggie_analytics/assistive_plane/service_runtime.py", "unattended refresh and dispatch cadence"),
            ("src/aggie_analytics/assistive_plane/cursor_backend.py", "Cursor idempotency, branch isolation, and budget lifecycle"),
            ("src/aggie_analytics/assistive_plane/orchestration.py", "routing identity immutability and workload accounting"),
            ("src/aggie_analytics/assistive_plane/budget.py", "reservation hard stops and settlement consistency"),
            ("src/aggie_analytics/assistive_plane/cpu_worker_backend.py", "signed request identity, replay, and bounded deterministic authority"),
            ("tools/run_unified_assistive_controller.py", "deployment configuration and fail-closed defaults"),
            ("tools/materialize_unified_assistive_inventory.py", "semantic evidence interpretation and route disposition integrity"),
        )
        review_targets.extend(
            (release_root / relative, focus, None, relative)
            for relative, focus in fixed_review_targets
        )
        for source, focus, source_jira_unit, relative_override in review_targets:
            if not source.is_file():
                continue
            relative = relative_override or source.name
            source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
            packet: dict[str, Any] = {
                "schema_version": 1,
                "provider": "cursor",
                "task_format": CURSOR_TASK_FORMAT,
                "jira_unit": "POST-SUBTASK-202",
                "schema_sha256": CURSOR_SCHEMA_SHA256,
                "source_hashes": [source_sha256, sha256_value({"release_commit": release_commit})],
                "dependencies": [],
                "pre_routing_effort_points": 5,
                "scope": f"Controller-routed candidate-only review of {relative}: {focus}.",
                "repository_url": "https://github.com/KevinSGarrett/BatteredAggieSyndrome.git",
                "starting_ref": release_commit,
                "base_commit": release_commit,
                "model": "gpt-5.3-codex",
                "reasoning": "medium",
                "fast": False,
                "work_on_current_branch": False,
                "auto_create_pr": False,
                "max_reservation_usd": "2.00",
                "prompt": (
                    f"Perform an independent candidate-only review of {relative} at exact base commit "
                    f"{release_commit}. Focus only on {focus}. Trace relevant callers and tests when "
                    "needed, but do not modify files, create commits, push branches, or open a PR. "
                    "Return evidence-backed findings with exact file/line references and severity. "
                    "Do not read or expose .env, credentials, private raw data, or protected evidence. "
                    "You have no canonical, protected, Git, Jira, forecast, model-promotion, BAS, or "
                    "publication authority."
                ),
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            if source_jira_unit is not None:
                packet["source_jira_unit"] = source_jira_unit
            data = canonical_json_bytes(packet) + b"\n"
            digest = hashlib.sha256(data).hexdigest()
            work_unit_id = "AUTO-CURSOR-" + digest[:20]
            if self.state.work_unit_states({work_unit_id}).get(work_unit_id) in TERMINAL_STATES:
                continue
            destination = queue_root / "continuous" / "sha256" / digest[:2] / f"{digest}.json"
            if destination.exists() and destination.read_bytes() != data:
                raise RuntimeError("CONTINUOUS_CURSOR_PACKET_COLLISION")
            if not destination.exists():
                _atomic_write(destination, data)
            created.append(
                {
                    "provider": "cursor",
                    "source_relative_path": relative,
                    "source_sha256": source_sha256,
                    "packet_path": str(destination),
                    "packet_sha256": digest,
                }
            )
            if len(created) >= 2:
                break
        return created

    def _materialize_cursor_implementation_work(
        self,
        *,
        snapshot: dict[str, Any],
        release_commit: str,
        limit: int = 1,
    ) -> list[dict[str, str]]:
        queue_root = self.config.provider_work_root
        project_root = self.config.project_root
        if queue_root is None or project_root is None or limit <= 0:
            return []
        ready = {
            str(record["jira_key"]): (source, record, source_sha256)
            for source, record, source_sha256 in self._jira_ready_records(
                limit=MAX_PROVIDER_WORK_UNITS
            )
        }
        created: list[dict[str, str]] = []
        seen_source_jira_units: set[str] = set()
        for candidate in self.state.cursor_review_candidates(limit=32):
            routed_packet = self._load_routed_cursor_review_packet(candidate)
            if routed_packet is None:
                continue
            review_packet, review_packet_sha256 = routed_packet
            if not self._cursor_review_matches_release(review_packet, release_commit):
                continue
            source_jira_unit = str(review_packet["source_jira_unit"])
            if source_jira_unit in seen_source_jira_units:
                continue
            seen_source_jira_units.add(source_jira_unit)
            ready_record = ready.get(source_jira_unit)
            if ready_record is None:
                continue
            source, record, source_sha256 = ready_record
            result_path = Path(str(candidate["result_artifact_path"]))
            if not result_path.is_file():
                continue
            result_raw = result_path.read_bytes()
            result_sha256 = hashlib.sha256(result_raw).hexdigest()
            if result_sha256 != candidate["result_artifact_sha256"]:
                continue
            result_payload = json.loads(result_raw)
            cursor_result = result_payload.get("result")
            run = cursor_result.get("run") if isinstance(cursor_result, dict) else None
            review_text = run.get("result") if isinstance(run, dict) else None
            if (
                result_payload.get("provider") != "cursor"
                or result_payload.get("authority") != "CANDIDATE_ONLY"
                or result_payload.get("validation_errors") != []
                or not isinstance(review_text, str)
                or not review_text.strip()
            ):
                continue
            allowed_paths = sorted(
                {
                    str(path)
                    for path in record.get("allowed_modification_paths", [])
                    if _safe_cursor_repository_path(path)
                }
            )
            if not allowed_paths:
                continue
            required_tests = sorted(
                {
                    str(item.get("path"))
                    for item in record.get("required_tests", [])
                    if isinstance(item, dict)
                    and isinstance(item.get("path"), str)
                    and item.get("path") not in {"MANUAL", "ISSUE_COMPLETION_MANIFEST"}
                }
            )
            bounded_review = review_text.strip()[:12000]
            packet: dict[str, Any] = {
                "schema_version": 1,
                "provider": "cursor",
                "task_format": CURSOR_IMPLEMENTATION_TASK_FORMAT,
                "jira_unit": "POST-SUBTASK-202",
                "source_jira_unit": source_jira_unit,
                "source_review_work_unit_id": str(candidate["work_unit_id"]),
                "source_review_attempt_id": str(candidate["attempt_id"]),
                "source_review_result_sha256": result_sha256,
                "source_review_disposition_sha256": str(
                    candidate["downstream_disposition_sha256"]
                ),
                "schema_sha256": CURSOR_IMPLEMENTATION_SCHEMA_SHA256,
                "source_hashes": [
                    source_sha256,
                    review_packet_sha256,
                    result_sha256,
                    str(candidate["downstream_disposition_sha256"]),
                ],
                "dependencies": [str(candidate["work_unit_id"])],
                "pre_routing_effort_points": 5,
                "scope": (
                    f"Controller-routed candidate implementation of {record['local_id']} "
                    f"after validated Cursor review {candidate['attempt_id']}"
                ),
                "repository_url": "https://github.com/KevinSGarrett/BatteredAggieSyndrome.git",
                "starting_ref": release_commit,
                "base_commit": release_commit,
                "model": "gpt-5.3-codex",
                "reasoning": "medium",
                "fast": False,
                "work_on_current_branch": False,
                "auto_create_pr": False,
                "max_reservation_usd": "2.00",
                "allowed_paths": allowed_paths,
                "required_tests": required_tests,
                "prompt": (
                    f"Implement the bounded Jira unit {record['local_id']} ({source_jira_unit}) "
                    f"at exact base {release_commit}. Modify only these exact paths: "
                    f"{json.dumps(allowed_paths, separators=(',', ':'))}. Run the applicable "
                    f"tests from {json.dumps(required_tests, separators=(',', ':'))}. Preserve "
                    "negative findings and do not weaken PIT, leakage, security, provenance, or "
                    "protected controls. Do not read .env or credentials. The result is "
                    "candidate-only and requires independent diff/path/test review. Commit and "
                    "push the candidate changes "
                    "to the generated isolated Cursor branch so the controller can fetch and "
                    "validate the complete diff. Do not mutate the base/current-main branch, "
                    "do not open a PR, and do not leave the candidate only as uncommitted "
                    "workspace changes. The prior candidate review follows:\n"
                    + bounded_review
                ),
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            data = canonical_json_bytes(packet) + b"\n"
            digest = hashlib.sha256(data).hexdigest()
            work_unit_id = "AUTO-CURSOR-" + digest[:20]
            if self.state.work_unit_states({work_unit_id}).get(work_unit_id) in TERMINAL_STATES:
                continue
            destination = (
                queue_root
                / "continuous"
                / "sha256"
                / digest[:2]
                / f"{digest}.json"
            )
            if destination.exists() and destination.read_bytes() != data:
                raise RuntimeError("CONTINUOUS_CURSOR_IMPLEMENTATION_PACKET_COLLISION")
            if not destination.exists():
                _atomic_write(destination, data)
            created.append(
                {
                    "provider": "cursor",
                    "source_relative_path": source.relative_to(
                        project_root.resolve(strict=True)
                    ).as_posix(),
                    "source_sha256": source_sha256,
                    "packet_path": str(destination),
                    "packet_sha256": digest,
                }
            )
            if len(created) >= limit:
                break
        return created

    def _materialize_continuous_cpu_work(
        self,
        snapshot: dict[str, Any],
        demand: dict[str, Any],
    ) -> list[dict[str, str]]:
        queue_root = self.config.provider_work_root
        cpu = demand.get("providers", {}).get("remote_cpu_worker", {})
        if (
            queue_root is None
            or not cpu.get("unmet")
            or cpu.get("admission_suspended")
            or int(cpu.get("active_execution_packets", 0)) > 0
            or int(cpu.get("pending_review_results", 0)) > 0
        ):
            return []
        historical_root = self.config.manifests_root.resolve(strict=False)
        if not historical_root.is_dir():
            return []
        candidates, _ = _bounded_top_level_json_scan(
            historical_root,
            limit=MAX_HISTORICAL_MANIFEST_SCAN_UNITS,
            name_prefix="snap_",
        )
        candidates = sorted(
            (path for path in candidates if path.name.startswith("snap_")),
            key=lambda path: (-path.stat().st_mtime_ns, path.as_posix()),
        )
        tranches: dict[str, list[tuple[Path, str, int, str]]] = {}
        for source in candidates:
            raw = source.read_bytes()
            if not 0 < len(raw) <= MAX_DISCOVERED_MANIFEST_BYTES:
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                continue
            dataset = value.get("dataset")
            if not isinstance(dataset, str) or not dataset.strip():
                dataset = "unclassified_snapshot_manifest"
            source_sha256 = hashlib.sha256(raw).hexdigest()
            line = json.dumps(value, sort_keys=True, separators=(",", ":"))
            tranches.setdefault(dataset, []).append((source, source_sha256, len(raw), line))
        # Prefer the largest natural source-defined tranche. Tiny datasets remain
        # eligible, but they must not crowd out the substantive historical batch
        # that can actually displace coordinator work.
        ordered_datasets = sorted(
            tranches,
            key=lambda dataset: (
                -len(tranches[dataset]),
                -sum(item[2] for item in tranches[dataset]),
                dataset,
            ),
        )
        for dataset in ordered_datasets:
            records = sorted(tranches[dataset], key=lambda item: item[0].as_posix())
            batches: list[list[tuple[Path, str, int, str]]] = []
            current: list[tuple[Path, str, int, str]] = []
            current_payload_bytes = 0
            for item in records:
                line_bytes = len(item[3].encode("utf-8"))
                if current and (
                    len(current) >= MAX_RECORDS
                    or current_payload_bytes + line_bytes > MAX_DISCOVERED_MANIFEST_BYTES
                ):
                    batches.append(current)
                    current = []
                    current_payload_bytes = 0
                current.append(item)
                current_payload_bytes += line_bytes
            if current:
                batches.append(current)
            for batch_index, batch_sources in enumerate(batches, start=1):
                batch_lines = [item[3] for item in batch_sources]
                batch_bytes = sum(item[2] for item in batch_sources)
                packet = {
                    "schema_version": 1,
                    "provider": "remote_cpu_worker",
                    "task": "LINE_HASH_MANIFEST",
                    "task_format": CPU_LINE_HASH_TASK_FORMAT,
                    "jira_unit": "BAT-563",
                    "schema_sha256": CPU_LINE_HASH_SCHEMA_SHA256,
                    "source_hashes": [item[1] for item in batch_sources],
                    "dependencies": [],
                    "pre_routing_effort_points": 3 if len(batch_lines) < 128 else 5,
                    "scope": (
                        "Controller-routed bounded historical-manifest hashing and replay-verification "
                        f"tranche for dataset {dataset}, batch {batch_index} of {len(batches)}, covering "
                        f"{len(batch_lines)} immutable captures and {batch_bytes} source bytes."
                    ),
                    "source_defined_tranche": {
                        "dataset": dataset,
                        "batch_index": batch_index,
                        "batch_count": len(batches),
                    },
                    "downstream_consumer": "HISTORICAL_MANIFEST_PROVENANCE_AND_REPLAY_VALIDATION",
                    "downstream_consumer_contract_version": CPU_LINE_HASH_DOWNSTREAM_CONSUMER_VERSION,
                    "delegation_preference_reason": "BOUNDED_FIXED_FUNCTION_REMOTE_CPU_BATCH_AVOIDS_COORDINATOR_SERIAL_HASHING",
                    "input_metrics": {
                        "documents": len(batch_lines),
                        "records": len(batch_lines),
                        "bytes": batch_bytes,
                    },
                    "payload": {"lines": batch_lines},
                    "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
                }
                data = canonical_json_bytes(packet) + b"\n"
                digest = hashlib.sha256(data).hexdigest()
                work_unit_id = "AUTO-CPU-LINE-HASH-" + digest[:20]
                if self.state.work_unit_states({work_unit_id}).get(work_unit_id) in TERMINAL_STATES:
                    continue
                destination = queue_root / "continuous" / "sha256" / digest[:2] / f"{digest}.json"
                if destination.exists() and destination.read_bytes() != data:
                    raise RuntimeError("CONTINUOUS_CPU_PACKET_COLLISION")
                if not destination.exists():
                    _atomic_write(destination, data)
                return [{
                    "provider": "remote_cpu_worker",
                    "source_relative_path": "BATCH:" + ",".join(
                        item[0].relative_to(historical_root).as_posix() for item in batch_sources[:8]
                    ),
                    "source_sha256": hashlib.sha256(
                        "".join(item[1] for item in batch_sources).encode()
                    ).hexdigest(),
                    "packet_path": str(destination),
                    "packet_sha256": digest,
                }]
        return []

    def _materialize_continuous_bge_work(
        self,
        demand: dict[str, Any],
    ) -> list[dict[str, str]]:
        queue_root = self.config.provider_work_root
        data_root = self.config.manifests_root.parent.resolve(strict=False)
        local = demand.get("providers", {}).get("ollama_local", {})
        if (
            queue_root is None
            or self.config.bge_downstream_consumer_contract_version is None
            or not local.get("unmet")
            or local.get("admission_suspended")
            or int(local.get("active_execution_packets", 0)) > 0
            or int(local.get("pending_review_results", 0)) > 0
        ):
            return []
        source_root = data_root / "reconciliation" / "historical_expansion"
        records: list[tuple[Path, str, str]] = []
        if source_root.is_dir():
            sources, _ = _bounded_json_scan(source_root, limit=128)
            for source in sources:
                raw = source.read_bytes()
                if not 0 < len(raw) <= MAX_DISCOVERED_MANIFEST_BYTES:
                    continue
                value = json.loads(raw)
                if not isinstance(value, dict):
                    continue
                compact = json.dumps(
                    {
                        "artifact_type": value.get("artifact_type"),
                        "decision_unit": value.get("decision_unit"),
                        "classification": value.get("classification"),
                        "negative_findings": value.get("negative_findings", []),
                        "next_action": value.get("next_action"),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )[:3000]
                records.append((source, hashlib.sha256(raw).hexdigest(), compact))
        manifest_sources, _ = _bounded_top_level_json_scan(
            self.config.manifests_root.resolve(strict=False),
            limit=MAX_HISTORICAL_MANIFEST_SCAN_UNITS,
            name_prefix="snap_",
        )
        manifest_sources = sorted(
            (path for path in manifest_sources if path.name.startswith("snap_")),
            key=lambda path: (-path.stat().st_mtime_ns, path.as_posix()),
        )[:256]
        for source in manifest_sources:
            raw = source.read_bytes()
            if not 0 < len(raw) <= MAX_DISCOVERED_MANIFEST_BYTES:
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                continue
            compact = json.dumps(
                {
                    "dataset": value.get("dataset"),
                    "source_id": value.get("source_id"),
                    "row_count": value.get("row_count"),
                    "schema_fields": value.get("schema_fields", []),
                    "route": value.get("metadata", {}).get("selected_route_id"),
                    "retrieved_at": value.get("retrieved_at"),
                },
                sort_keys=True,
                separators=(",", ":"),
            )[:3000]
            records.append((source, hashlib.sha256(raw).hexdigest(), compact))
        if len(records) < 2:
            return []
        records.sort(key=lambda item: (-item[0].stat().st_mtime_ns, item[0].as_posix()))
        created: list[dict[str, str]] = []
        for query_source, query_sha256, query_text in records:
            candidates = [item for item in records if item[1] != query_sha256][:16]
            if not candidates:
                continue
            packet = {
                "schema_version": 1,
                "provider": "ollama_local",
                "model": BGE_MODEL,
                "model_digest": BGE_MODEL_DIGEST,
                "task_format": BGE_TASK_FORMAT,
                "policy_version": BGE_POLICY_VERSION,
                "prompt_version": BGE_PROMPT_VERSION,
                "route_schema_version": BGE_SCHEMA_VERSION,
                "schema_sha256": BGE_SCHEMA_SHA256,
                "jira_unit": "BAT-562",
                "source_hashes": [query_sha256, *[item[1] for item in candidates]],
                "dependencies": [],
                "pre_routing_effort_points": 2,
                "scope": (
                    "Candidate-only semantic retrieval of comparable historical reconciliation "
                    f"evidence for {query_source.name}; no identity merge or canonical authority."
                ),
                "downstream_consumer_contract_version": (
                    self.config.bge_downstream_consumer_contract_version
                ),
                "query": (
                    "Rank prior historical reconciliation artifacts most comparable to this new "
                    "artifact for deduplication and review routing. " + query_text
                ),
                "candidates": [
                    {
                        "candidate_id": item[1],
                        "text": f"{item[0].name}: {item[2]}",
                    }
                    for item in candidates
                ],
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            data = canonical_json_bytes(packet) + b"\n"
            digest = hashlib.sha256(data).hexdigest()
            work_unit_id = "AUTO-BGE-" + digest[:20]
            if self.state.work_unit_states({work_unit_id}).get(work_unit_id) in TERMINAL_STATES:
                continue
            destination = queue_root / "continuous" / "sha256" / digest[:2] / f"{digest}.json"
            if destination.exists() and destination.read_bytes() != data:
                raise RuntimeError("CONTINUOUS_BGE_PACKET_COLLISION")
            if not destination.exists():
                _atomic_write(destination, data)
            created.append(
                {
                    "provider": "ollama_local",
                    "source_relative_path": query_source.relative_to(data_root).as_posix(),
                    "source_sha256": query_sha256,
                    "packet_path": str(destination),
                    "packet_sha256": digest,
                }
            )
            if len(created) >= 2:
                break
        return created

    def _materialize_openai_cross_provider_qa(
        self,
        *,
        queue_root: Path,
        schema_relative: str,
        schema_sha256: str,
        limit: int,
    ) -> list[dict[str, str]]:
        """Create bounded independent QA from immutable non-OpenAI candidates."""
        if limit <= 0:
            return []
        result_root = self.config.packet_root / "evidence" / "provider-results"
        if not result_root.is_dir():
            return []
        resolved_result_root = result_root.resolve(strict=True)
        task_name = "assistive_model_evaluation"
        task_definition = self._openai_task_definition(task_name)
        jira_unit = str(task_definition.get("jira_unit", ""))
        model = "gpt-5.6-luna"
        allowed_models = task_definition.get("allowed_models", [])
        allocation = str(task_definition.get("allocation_by_model", {}).get(model, ""))
        destination_name = str(task_definition.get("candidate_destination", ""))
        if (
            not jira_unit
            or model not in allowed_models
            or not allocation
            or destination_name not in {"CANDIDATE", "REVIEW", "QUARANTINE"}
        ):
            raise ValueError("RUNTIME_INVENTORY_OPENAI_CROSS_PROVIDER_TASK_BINDING_INVALID")

        scanned, _ = _bounded_json_scan(
            resolved_result_root, limit=MAX_PROVIDER_WORK_SCAN_UNITS
        )
        allowed_providers = {
            "cursor": 0,
            "openrouter": 1,
            "ollama_local": 2,
            "remote_cpu_worker": 3,
        }
        by_provider: dict[str, list[tuple[int, Path, dict[str, Any], bytes, str]]] = {
            provider: [] for provider in allowed_providers
        }
        for source in scanned:
            try:
                modified_ns = source.stat().st_mtime_ns
                raw = source.read_bytes()
                if not 0 < len(raw) <= 12000:
                    continue
                source_capture_sha256 = hashlib.sha256(raw).hexdigest()
                relative_parts = source.relative_to(resolved_result_root).parts
                if (
                    len(relative_parts) != 3
                    or relative_parts[0] != "sha256"
                    or relative_parts[1] != source_capture_sha256
                    or relative_parts[2] != "report.json"
                ):
                    continue
                value = json.loads(raw)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if not isinstance(value, dict):
                continue
            provider = str(value.get("provider", ""))
            validation_errors = value.get("validation_errors")
            candidate = value.get("result")
            if (
                provider not in allowed_providers
                or value.get("schema_version") != 1
                or value.get("artifact_type") != "GOVERNED_PROVIDER_CANDIDATE_RESULT"
                or value.get("authority") != "CANDIDATE_ONLY"
                or value.get("disposition") != "REVIEW_ONLY"
                or validation_errors != []
                or not isinstance(value.get("work_unit_id"), str)
                or not value["work_unit_id"]
                or not isinstance(candidate, dict)
                or candidate.get("authority") != "CANDIDATE_ONLY"
                or candidate.get("canonical_writes") != 0
                or candidate.get("protected_decisions") != 0
            ):
                continue
            by_provider[provider].append(
                (modified_ns, source, value, raw, source_capture_sha256)
            )

        bounded_candidates: list[tuple[int, int, Path, dict[str, Any], bytes, str]] = []
        for provider, priority in allowed_providers.items():
            newest = sorted(
                by_provider[provider], key=lambda item: (-item[0], item[1].as_posix())
            )[:MAX_OPENAI_CROSS_PROVIDER_QA_RESULTS_PER_PROVIDER]
            bounded_candidates.extend(
                (priority, *item) for item in newest
            )
        bounded_candidates.sort(key=lambda item: (item[0], -item[1], item[2].as_posix()))

        created: list[dict[str, str]] = []
        selected_providers: set[str] = set()
        seen_source_hashes: set[str] = set()
        for _priority, _modified_ns, source, value, _raw, source_capture_sha256 in bounded_candidates:
            provider = str(value["provider"])
            if provider in selected_providers or source_capture_sha256 in seen_source_hashes:
                continue
            seen_source_hashes.add(source_capture_sha256)
            excerpt_value = {
                "artifact_type": value["artifact_type"],
                "authority": value["authority"],
                "candidate_result": value["result"],
                "provider": provider,
                "source_disposition": value["disposition"],
                "source_work_unit_id": value["work_unit_id"],
            }
            excerpt = json.dumps(excerpt_value, sort_keys=True, separators=(",", ":"))
            if not 0 < len(excerpt) <= 12000:
                continue
            excerpt_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
            prompt = (
                "Independently assess only the supplied validated candidate result from another governed "
                f"assistive route ({provider}). Do not accept it, invent facts, repeat provider confidence as "
                "evidence, or authorize canonical/PIT/training/protected/forecast/merge/publication changes. "
                f"Return task_id exactly {task_name}, source_capture_sha256 exactly "
                f"{source_capture_sha256}, and disposition {destination_name}. Return candidate-only facts for "
                "source_provider, candidate_disposition, evidence_quality, and deterministic_follow_up. Every "
                f"SUPPORTED fact must cite exactly source_capture_sha256 {source_capture_sha256}, locator "
                f"evidence:1, and excerpt_sha256 {excerpt_sha256}. Use UNKNOWN or NOT_PRESENT with no evidence "
                "when the candidate does not support a conclusion. Preserve conflicts and limitations."
            )
            packet = {
                "schema_version": 1,
                "provider": "openai_direct",
                "task_format": "governed_openai_candidate_v1",
                "jira_unit": jira_unit,
                "schema_sha256": schema_sha256,
                "source_hashes": [source_capture_sha256, excerpt_sha256],
                "dependencies": [],
                "pre_routing_effort_points": 3,
                "scope": (
                    "Candidate-only independent QA of "
                    f"{provider} result {value['work_unit_id']}"
                ),
                "job": {
                    "task_name": task_name,
                    "jira_unit": jira_unit,
                    "source_url": source.resolve().as_uri(),
                    "source_capture_sha256": source_capture_sha256,
                    "source_excerpt": excerpt,
                    "prompt": prompt,
                    "prompt_version": "continuous-cross-provider-candidate-qa-v1",
                    "schema_path": schema_relative,
                    "schema_version": "1",
                    "model": model,
                    "reasoning_effort": "low",
                    "allocation": allocation,
                    "destination": destination_name,
                    "max_output_tokens": 1600,
                    "priority": "NORMAL",
                    "release_reason": None,
                    "admission_review_id": None,
                    "source_image_path": None,
                    "source_image_mime_type": None,
                    "source_image_detail": None,
                },
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            data = canonical_json_bytes(packet) + b"\n"
            digest = hashlib.sha256(data).hexdigest()
            work_unit_id = "AUTO-OAI-" + digest[:20]
            if self.state.work_unit_states({work_unit_id}).get(work_unit_id) in TERMINAL_STATES:
                continue
            packet_path = queue_root / "continuous" / "sha256" / digest[:2] / f"{digest}.json"
            if packet_path.exists() and packet_path.read_bytes() != data:
                raise RuntimeError("CONTINUOUS_OPENAI_CROSS_PROVIDER_PACKET_COLLISION")
            if not packet_path.exists():
                _atomic_write(packet_path, data)
            created.append(
                {
                    "provider": "openai_direct",
                    "source_relative_path": source.relative_to(
                        resolved_result_root
                    ).as_posix(),
                    "source_sha256": source_capture_sha256,
                    "packet_path": str(packet_path),
                    "packet_sha256": digest,
                }
            )
            selected_providers.add(provider)
            if len(created) >= limit:
                break
        return created

    def _materialize_continuous_openai_work(
        self,
        demand: dict[str, Any],
    ) -> list[dict[str, str]]:
        queue_root = self.config.provider_work_root
        data_root = self.config.manifests_root.parent.resolve(strict=False)
        release_root = self.config.release_root
        openai = demand.get("providers", {}).get("openai_direct", {})
        if (
            queue_root is None
            or release_root is None
            or not openai.get("unmet")
            or openai.get("admission_suspended")
            or int(openai.get("active_execution_packets", 0)) > 0
        ):
            return []
        source_root = data_root / "quarantine"
        schema_relative = "schemas/openai/assistive_candidate.schema.json"
        schema = _verified_json(release_root / schema_relative)
        schema_sha256 = sha256_value(schema)
        created: list[dict[str, str]] = []
        sources: list[Path] = []
        if source_root.is_dir():
            sources, _ = _bounded_json_scan(source_root, limit=512)
            sources.sort(key=lambda path: (-path.stat().st_mtime_ns, path.as_posix()))
        for source in sources:
            relative = source.relative_to(source_root).as_posix()
            if "availability" in relative.lower():
                continue
            raw = source.read_bytes()
            if not 0 < len(raw) <= 10000:
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(value, dict):
                continue
            source_capture_sha256 = hashlib.sha256(raw).hexdigest()
            excerpt = json.dumps(value, sort_keys=True, separators=(",", ":"))
            excerpt_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
            difficult = any(token in relative.lower() for token in ("duplicate", "conflict", "schema"))
            model = "gpt-5.6-terra" if difficult else "gpt-5.6-luna"
            allocation = "TERRA_COMPLEX" if difficult else "LUNA_HARD_VOLUME"
            reasoning_effort = "medium" if difficult else "low"
            prompt = (
                "Classify only the supplied quarantined BAS evidence artifact for deterministic remediation. "
                "Do not infer absent facts, canonical identities, timestamps, PIT eligibility, labels, or statistics. "
                "Return task_id exactly quarantine_schema_classification, source_capture_sha256 exactly "
                f"{source_capture_sha256}, and disposition QUARANTINE. Return facts for artifact_type, "
                "quarantine_reason, remediation_route, and evidence_sufficiency. A SUPPORTED fact must cite "
                f"exactly source_capture_sha256 {source_capture_sha256}, locator evidence:1, and excerpt_sha256 "
                f"{excerpt_sha256}. Use UNKNOWN or NOT_PRESENT with no evidence when the source does not state "
                "the fact. Use conflicts and notes only for evidence-backed limitations. This output is candidate-only "
                "and has no canonical, PIT, training, protected, forecast, or publication authority."
            )
            packet = {
                "schema_version": 1,
                "provider": "openai_direct",
                "task_format": "governed_openai_candidate_v1",
                "jira_unit": "POST-SUBTASK-164",
                "schema_sha256": schema_sha256,
                "source_hashes": [source_capture_sha256, excerpt_sha256],
                "dependencies": [],
                "pre_routing_effort_points": 3,
                "scope": f"Candidate-only quarantine remediation classification for {relative}",
                "job": {
                    "task_name": "quarantine_schema_classification",
                    "jira_unit": "POST-SUBTASK-164",
                    "source_url": source.resolve().as_uri(),
                    "source_capture_sha256": source_capture_sha256,
                    "source_excerpt": excerpt,
                    "prompt": prompt,
                    "prompt_version": "continuous-quarantine-remediation-v1",
                    "schema_path": schema_relative,
                    "schema_version": "1",
                    "model": model,
                    "reasoning_effort": reasoning_effort,
                    "allocation": allocation,
                    "destination": "QUARANTINE",
                    "max_output_tokens": 4096,
                    "priority": "NORMAL",
                    "release_reason": None,
                    "admission_review_id": None,
                    "source_image_path": None,
                    "source_image_mime_type": None,
                    "source_image_detail": None,
                },
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            data = canonical_json_bytes(packet) + b"\n"
            digest = hashlib.sha256(data).hexdigest()
            work_unit_id = "AUTO-OAI-" + digest[:20]
            if self.state.work_unit_states({work_unit_id}).get(work_unit_id) in TERMINAL_STATES:
                continue
            destination = queue_root / "continuous" / "sha256" / digest[:2] / f"{digest}.json"
            if destination.exists() and destination.read_bytes() != data:
                raise RuntimeError("CONTINUOUS_OPENAI_PACKET_COLLISION")
            if not destination.exists():
                _atomic_write(destination, data)
            created.append(
                {
                    "provider": "openai_direct",
                    "source_relative_path": relative,
                    "source_sha256": source_capture_sha256,
                    "packet_path": str(destination),
                    "packet_sha256": digest,
                }
            )
            if len(created) >= 2:
                break
        if len(created) >= 2:
            return created

        # The live historical-acquisition lane produces reconciliation and
        # feature-evaluation evidence before it produces contest-detail pages.
        # Treat those bounded, immutable JSON artifacts as real candidate-only
        # review work so the direct-OpenAI route does not depend on a finite
        # collection of gamebook-format probes.  These tasks may identify
        # follow-up work, but they retain no canonical or protected authority.
        review_sources = (
            (
                "entity_review",
                data_root / "reconciliation" / "historical_expansion",
                "Review only the supplied historical reconciliation evidence. Identify explicit unresolved "
                "populations, ambiguity drivers, and deterministic follow-up routes. Do not approve an entity "
                "merge, infer a missing identity, or claim historical completeness.",
                "continuous-historical-reconciliation-review-v1",
                "gpt-5.6-terra",
                "medium",
            ),
            (
                "assistive_model_evaluation",
                data_root / "reconciliation" / "feature_engineering",
                "Independently challenge only the supplied preliminary feature or evaluation artifact. Identify "
                "explicit evidence gaps, leakage risks, unsupported claims, and deterministic checks. Do not "
                "promote a feature, model, protected result, A&M lift, BAS, or Aggie Excess conclusion.",
                "continuous-preliminary-evidence-qa-v1",
                "gpt-5.6-luna",
                "low",
            ),
        )
        for task_name, review_root, instruction, prompt_version, model, reasoning_effort in review_sources:
            if len(created) >= 2:
                break
            if not review_root.is_dir():
                continue
            task_definition = self._openai_task_definition(task_name)
            jira_unit = str(task_definition.get("jira_unit", ""))
            allowed_models = task_definition.get("allowed_models", [])
            allocation = str(task_definition.get("allocation_by_model", {}).get(model, ""))
            destination = str(task_definition.get("candidate_destination", ""))
            if (
                not jira_unit
                or model not in allowed_models
                or not allocation
                or destination not in {"CANDIDATE", "REVIEW", "QUARANTINE"}
            ):
                raise ValueError("RUNTIME_INVENTORY_OPENAI_REVIEW_TASK_BINDING_INVALID")
            scanned, _ = _bounded_json_scan(review_root, limit=256)
            candidates = sorted(
                (
                    path
                    for path in scanned
                    if 0 < path.stat().st_size <= 12000
                ),
                key=lambda path: (-path.stat().st_mtime_ns, path.as_posix()),
            )
            for source in candidates:
                raw = source.read_bytes()
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(value, dict):
                    continue
                source_capture_sha256 = hashlib.sha256(raw).hexdigest()
                excerpt = json.dumps(value, sort_keys=True, separators=(",", ":"))
                if len(excerpt) > 12000:
                    continue
                excerpt_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
                relative = source.relative_to(data_root.resolve(strict=True)).as_posix()
                prompt = (
                    instruction
                    + f" Return task_id exactly {task_name}, source_capture_sha256 exactly "
                    + f"{source_capture_sha256}, and disposition {destination}. Every SUPPORTED fact must cite exactly "
                    + f"source_capture_sha256 {source_capture_sha256}, locator evidence:1, and excerpt_sha256 "
                    + f"{excerpt_sha256}. Use UNKNOWN or NOT_PRESENT with no evidence when the artifact does not "
                    + "state the fact. This output is candidate-only and cannot alter canonical data, PIT state, "
                    + "training, protected evaluation, model promotion, forecasts, or publication."
                )
                packet = {
                    "schema_version": 1,
                    "provider": "openai_direct",
                    "task_format": "governed_openai_candidate_v1",
                    "jira_unit": jira_unit,
                    "schema_sha256": schema_sha256,
                    "source_hashes": [source_capture_sha256, excerpt_sha256],
                    "dependencies": [],
                    "pre_routing_effort_points": 3,
                    "scope": f"Candidate-only {task_name} for {relative}",
                    "job": {
                        "task_name": task_name,
                        "jira_unit": jira_unit,
                        "source_url": source.resolve().as_uri(),
                        "source_capture_sha256": source_capture_sha256,
                        "source_excerpt": excerpt,
                        "prompt": prompt,
                        "prompt_version": prompt_version,
                        "schema_path": schema_relative,
                        "schema_version": "1",
                        "model": model,
                        "reasoning_effort": reasoning_effort,
                        "allocation": allocation,
                        "destination": destination,
                        "max_output_tokens": 4096,
                        "priority": "NORMAL",
                        "release_reason": None,
                        "admission_review_id": None,
                        "source_image_path": None,
                        "source_image_mime_type": None,
                        "source_image_detail": None,
                    },
                    "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
                }
                data = canonical_json_bytes(packet) + b"\n"
                digest = hashlib.sha256(data).hexdigest()
                work_unit_id = "AUTO-OAI-" + digest[:20]
                if self.state.work_unit_states({work_unit_id}).get(work_unit_id) in TERMINAL_STATES:
                    continue
                destination = queue_root / "continuous" / "sha256" / digest[:2] / f"{digest}.json"
                if destination.exists() and destination.read_bytes() != data:
                    raise RuntimeError("CONTINUOUS_OPENAI_REVIEW_PACKET_COLLISION")
                if not destination.exists():
                    _atomic_write(destination, data)
                created.append(
                    {
                        "provider": "openai_direct",
                        "source_relative_path": relative,
                        "source_sha256": source_capture_sha256,
                        "packet_path": str(destination),
                        "packet_sha256": digest,
                    }
                )
                break
        if len(created) >= 2:
            return created

        task_name = "gamebook_schema_mapping"
        task_definition = self._openai_task_definition(task_name)
        jira_unit = str(task_definition.get("jira_unit", ""))
        allowed_models = task_definition.get("allowed_models", [])
        model = "gpt-5.6-terra"
        allocation = str(task_definition.get("allocation_by_model", {}).get(model, ""))
        if not jira_unit or model not in allowed_models or not allocation:
            raise ValueError("RUNTIME_INVENTORY_OPENAI_GAMEBOOK_TASK_BINDING_INVALID")
        manifest_sources, _ = _bounded_top_level_json_scan(
            self.config.manifests_root.resolve(strict=False),
            limit=MAX_HISTORICAL_MANIFEST_SCAN_UNITS,
            name_prefix="snap_",
        )
        gamebook_datasets = {
            "ncaa_contest_box_score",
            "ncaa_contest_drives",
            "ncaa_contest_individual_stats",
            "ncaa_contest_officials",
            "ncaa_contest_play_by_play",
            "ncaa_contest_team_stats",
        }
        candidates: list[tuple[int, int, Path, dict[str, Any]]] = []
        for manifest_path in manifest_sources:
            manifest = _verified_json(manifest_path)
            dataset = manifest.get("dataset")
            if dataset not in gamebook_datasets:
                continue
            fields = manifest.get("schema_fields", [])
            field_count = len(fields) if isinstance(fields, list) else 999
            candidates.append(
                (0 if field_count == 0 else 1, field_count, manifest_path, manifest)
            )
        candidates.sort(
            key=lambda item: (
                item[0],
                item[1],
                -item[2].stat().st_mtime_ns,
                item[2].as_posix(),
            )
        )
        resolved_data_root = data_root.resolve(strict=True)
        for _empty_rank, _field_count, manifest_path, manifest in candidates:
            relative_raw = manifest.get("relative_path")
            raw_sha256 = manifest.get("raw_sha256")
            source_uri = manifest.get("source_uri")
            if (
                not isinstance(relative_raw, str)
                or not relative_raw
                or not self._valid_sha256(raw_sha256)
                or not isinstance(source_uri, str)
                or not source_uri
            ):
                continue
            try:
                raw_path = (resolved_data_root / relative_raw).resolve(strict=True)
            except OSError:
                continue
            if resolved_data_root not in raw_path.parents or not raw_path.is_file():
                continue
            raw = raw_path.read_bytes()
            if not 0 < len(raw) <= MAX_PROVIDER_WORK_BYTES:
                continue
            if hashlib.sha256(raw).hexdigest() != raw_sha256:
                continue
            excerpt = _bounded_html_text(raw)
            if len(excerpt) < 100:
                continue
            excerpt_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
            manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            dataset = str(manifest["dataset"])
            prompt = (
                "Map only the fields and sections explicitly present in this NCAA gamebook-equivalent "
                "page excerpt. Do not invent plays, statistics, timestamps, identities, or completeness. "
                f"Return task_id exactly {task_name}, source_capture_sha256 exactly {raw_sha256}, and "
                "disposition REVIEW. Return scalar facts for page_dataset, observed_section_labels, "
                "field_mapping_candidate, and deterministic_parser_gap. Every SUPPORTED fact must cite "
                f"source_capture_sha256 {raw_sha256}, locator evidence:1, and excerpt_sha256 "
                f"{excerpt_sha256}. Use UNKNOWN or NOT_PRESENT with null value and no evidence when absent. "
                "This is candidate-only schema interpretation with no canonical, PIT, training, protected, "
                "forecast, model-promotion, BAS, or publication authority."
            )
            packet = {
                "schema_version": 1,
                "provider": "openai_direct",
                "task_format": "governed_openai_candidate_v1",
                "jira_unit": jira_unit,
                "schema_sha256": schema_sha256,
                "source_hashes": [raw_sha256, excerpt_sha256, manifest_sha256],
                "dependencies": [],
                "pre_routing_effort_points": 5,
                "scope": (
                    "Candidate-only NCAA gamebook-equivalent schema mapping for "
                    f"{dataset} capture {raw_sha256[:12]}"
                ),
                "job": {
                    "task_name": task_name,
                    "jira_unit": jira_unit,
                    "source_url": source_uri,
                    "source_capture_sha256": raw_sha256,
                    "source_excerpt": excerpt,
                    "prompt": prompt,
                    "prompt_version": "continuous-gamebook-schema-mapping-v1",
                    "schema_path": schema_relative,
                    "schema_version": "1",
                    "model": model,
                    "reasoning_effort": "medium",
                    "allocation": allocation,
                    "destination": "REVIEW",
                    "max_output_tokens": 1600,
                    "priority": "HIGH",
                    "release_reason": None,
                    "admission_review_id": None,
                    "source_image_path": None,
                    "source_image_mime_type": None,
                    "source_image_detail": None,
                },
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            data = canonical_json_bytes(packet) + b"\n"
            digest = hashlib.sha256(data).hexdigest()
            work_unit_id = "AUTO-OAI-" + digest[:20]
            if self.state.work_unit_states({work_unit_id}).get(work_unit_id) in TERMINAL_STATES:
                continue
            destination = queue_root / "continuous" / "sha256" / digest[:2] / f"{digest}.json"
            if destination.exists() and destination.read_bytes() != data:
                raise RuntimeError("CONTINUOUS_OPENAI_GAMEBOOK_PACKET_COLLISION")
            if not destination.exists():
                _atomic_write(destination, data)
            created.append(
                {
                    "provider": "openai_direct",
                    "source_relative_path": relative_raw,
                    "source_sha256": str(raw_sha256),
                    "packet_path": str(destination),
                    "packet_sha256": digest,
                }
            )
            if len(created) >= 2:
                break
        if len(created) < 2:
            created.extend(
                self._materialize_openai_cross_provider_qa(
                    queue_root=queue_root,
                    schema_relative=schema_relative,
                    schema_sha256=schema_sha256,
                    limit=2 - len(created),
                )
            )
        return created

    def _producer_watermarks(self, moment: datetime) -> dict[str, Any]:
        data_root = (
            self.config.continuous_source_root.parent
            if self.config.continuous_source_root is not None
            else self.config.manifests_root.parent
        )
        sources: dict[str, tuple[Path, frozenset[str] | None, int, bool]] = {
            "historical_snapshot_registry": (
                self.config.manifests_root,
                None,
                MAX_HISTORICAL_MANIFEST_SCAN_UNITS,
                True,
            ),
            "quarantine": (data_root / "quarantine", None, MAX_PROVIDER_WORK_SCAN_UNITS, False),
            "reconciliation": (data_root / "reconciliation", None, MAX_PROVIDER_WORK_SCAN_UNITS, False),
            "provider_request_queue": (
                self.config.provider_work_root or data_root / "assistive/provider_work/requests",
                None,
                MAX_PROVIDER_WORK_SCAN_UNITS,
                False,
            ),
            "provider_review_queue": (
                self.config.packet_root / "evidence/review-queue",
                None,
                MAX_PROVIDER_WORK_SCAN_UNITS,
                False,
            ),
            "provider_result_queue": (
                self.config.packet_root / "evidence/provider-results",
                frozenset({"report.json"}),
                MAX_PROVIDER_WORK_SCAN_UNITS,
                False,
            ),
        }
        if self.config.project_root is not None:
            sources["canonical_jira_records"] = (
                self.config.project_root / "jira" / "records" / "issues",
                None,
                MAX_PROVIDER_WORK_SCAN_UNITS,
                False,
            )
        watermarks: dict[str, Any] = {}
        for name, (root, allowed_names, scan_limit, top_level_snapshots) in sources.items():
            records: list[dict[str, Any]] = []
            scan_status = "PASS"
            finding = "SCAN_COMPLETE"
            if root.is_dir():
                try:
                    resolved_root = root.resolve(strict=True)
                    if top_level_snapshots:
                        candidates, capped = _bounded_top_level_json_scan(
                            resolved_root,
                            limit=scan_limit,
                            name_prefix="snap_",
                        )
                    else:
                        candidates, capped = _bounded_json_scan(
                            resolved_root,
                            limit=scan_limit,
                            allowed_names=allowed_names,
                        )
                    if capped:
                        scan_status = "INCOMPLETE"
                        finding = "SOURCE_SCAN_BOUND_REACHED"
                    for path in candidates:
                        try:
                            size = path.stat().st_size
                            if not 0 < size <= MAX_PROVIDER_WORK_BYTES:
                                continue
                            data = path.read_bytes()
                            records.append(
                                {
                                    "path": path.relative_to(resolved_root).as_posix(),
                                    "bytes": size,
                                    "sha256": hashlib.sha256(data).hexdigest(),
                                    "modified_ns": path.stat().st_mtime_ns,
                                }
                            )
                        except OSError:
                            scan_status = "INCOMPLETE"
                            finding = "SOURCE_ENTRY_READ_FAILED"
                except OSError:
                    scan_status = "FAIL"
                    finding = "SOURCE_SCAN_FAILED"
            else:
                finding = "SOURCE_ROOT_ABSENT_EMPTY_DENOMINATOR"
            watermarks[name] = {
                "root": str(root.resolve(strict=False)),
                "scanned_at": rfc3339(moment),
                "scan_status": scan_status,
                "finding": finding,
                "eligible_file_count": len(records),
                "latest_modified_ns": max((int(item["modified_ns"]) for item in records), default=None),
                "watermark_identity": sha256_value(records),
            }
        return {
            "schema_version": 1,
            "scan_interval_slo_seconds": 300,
            "sources": watermarks,
            "all_sources_scanned": all(
                item["scan_status"] == "PASS" for item in watermarks.values()
            ),
            "watermark_identity": sha256_value(watermarks),
        }

    def refresh(self, *, now: datetime | None = None) -> dict[str, Any]:
        moment = now or datetime.now(timezone.utc)
        self._jira_ready_cache = None
        base, base_sha256 = self._load_current_snapshot()
        live_external_evidence = self._live_external_evidence(base)
        base = {**base, "external_evidence": live_external_evidence}
        deployed_release = self._deployed_release()
        if deployed_release is not None:
            # Bind every producer and admission check to the release that is
            # executing this refresh. Waiting until final snapshot assembly
            # allows the first post-deploy cycle to emit packets for stale main.
            deployed_commit = deployed_release["build_commit"]
            base = {
                **base,
                "deployed_release": deployed_release,
                "git": {
                    "origin_main": deployed_commit,
                    "head": deployed_commit,
                    "deployed_head": deployed_commit,
                    "merged_main_identity_at_release_build": deployed_commit,
                    "status_porcelain_sha256": hashlib.sha256(b"").hexdigest(),
                    "status_evidence": "IMMUTABLE_RELEASE_TREE_NO_WORKTREE_MUTATION_SURFACE",
                    "evidence_scope": deployed_release["evidence_scope"],
                },
            }
        if not self._cpu_qualified(base):
            raise RuntimeError("RUNTIME_INVENTORY_CPU_QUALIFICATION_NOT_ESTABLISHED")

        prior_units = {
            item["work_unit_id"]: item
            for item in base.get("work_units", [])
            if str(item.get("work_unit_id", "")).startswith(DYNAMIC_PREFIXES)
        }
        prior_decisions = {
            item["work_unit_id"]: item
            for item in base.get("route_decisions", [])
            if str(item.get("work_unit_id", "")).startswith(DYNAMIC_PREFIXES)
        }
        execution_packets = dict(base.get("execution_packets", {}))
        work_unit_roles = dict(base.get("work_unit_roles", {}))
        if not work_unit_roles:
            work_unit_roles = {
                str(item["work_unit_id"]): ATOMIC_EXECUTABLE
                for item in base.get("work_units", [])
            }
        provider_work_findings: list[dict[str, str]] = []
        preliminary_demand = self._operational_demand(
            base,
            list(base.get("route_decisions", [])),
            work_unit_roles,
        )
        continuous_packets: list[dict[str, str]] = []
        producers = (
            ("openrouter", lambda: self._materialize_continuous_openrouter_work(base, preliminary_demand)),
            ("cursor", lambda: self._materialize_continuous_cursor_work(base, preliminary_demand)),
            ("remote_cpu_worker", lambda: self._materialize_continuous_cpu_work(base, preliminary_demand)),
            ("ollama_local", lambda: self._materialize_continuous_bge_work(preliminary_demand)),
            ("openai_direct", lambda: self._materialize_continuous_openai_work(preliminary_demand)),
        )
        for producer, compile_work in producers:
            try:
                continuous_packets.extend(compile_work())
            except (OSError, KeyError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                finding = {
                    "finding": type(exc).__name__ + ":" + str(exc)[:240],
                    "observed_at": rfc3339(moment),
                    "provider": producer,
                    "disposition": "EXACT_PRODUCER_FAILED_UNRELATED_PRODUCERS_CONTINUE",
                }
                provider_work_findings.append(finding)
                self.state.append_event("CONTINUOUS_WORK_PRODUCER_BLOCKED", finding, now=moment)
        try:
            provider_work = self._discover_provider_work(base, moment)
            provider_work_findings.extend(self._provider_packet_findings)
        except (OSError, KeyError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            finding = {
                "finding": type(exc).__name__ + ":" + str(exc)[:240],
                "observed_at": rfc3339(moment),
                "disposition": "PROVIDER_WORK_DEFERRED_CPU_AND_DETERMINISTIC_DISCOVERY_CONTINUES",
            }
            provider_work_findings.append(finding)
            self.state.append_event("PROVIDER_WORK_DISCOVERY_DEFERRED", finding, now=moment)
            provider_work = []
        discovered = [*self._discover(moment), *provider_work]
        for unit, decision, packet in discovered:
            prior_units.setdefault(unit.work_unit_id, asdict(unit))
            prior_decisions.setdefault(
                unit.work_unit_id,
                {**asdict(decision), "disposition": decision.disposition.value},
            )
            execution_packets.setdefault(unit.work_unit_id, packet)
            work_unit_roles.setdefault(unit.work_unit_id, ATOMIC_EXECUTABLE)

        release_commit = self._snapshot_release_commit(base)
        execution_packets = {
            work_unit_id: self._execution_packet_revision_metadata(reference, release_commit)
            for work_unit_id, reference in execution_packets.items()
        }

        status = self.state.work_unit_states(set(prior_units))
        for work_unit_id, current_state in status.items():
            if current_state == "CLOSED" and prior_decisions[work_unit_id]["disposition"] != RoutingDisposition.COMPLETED.value:
                prior_decisions[work_unit_id] = {
                    **prior_decisions[work_unit_id],
                    "disposition": RoutingDisposition.COMPLETED.value,
                    "provider": None,
                    "model": None,
                    "reason": "CONTROLLER_EXECUTION_CLOSED_WITH_DURABLE_EVIDENCE",
                    "decided_at": rfc3339(moment),
                }

        static_units = [
            item for item in base.get("work_units", [])
            if not str(item.get("work_unit_id", "")).startswith(DYNAMIC_PREFIXES)
        ]
        static_decisions = [
            item for item in base.get("route_decisions", [])
            if not str(item.get("work_unit_id", "")).startswith(DYNAMIC_PREFIXES)
        ]
        work_units = static_units + [prior_units[key] for key in sorted(prior_units)]
        route_decisions = static_decisions + [prior_decisions[key] for key in sorted(prior_decisions)]
        unit_by_id = {str(item["work_unit_id"]): item for item in work_units}
        revision_supersessions = self._derive_revision_supersessions(
            execution_packets=execution_packets,
            execution_states=status,
            release_commit=release_commit,
            prior=list(base.get("revision_supersessions", [])),
            observed_at=rfc3339(moment),
        )
        for decision in route_decisions:
            work_unit_id = str(decision.get("work_unit_id", ""))
            provider = decision.get("provider")
            unit = unit_by_id.get(work_unit_id)
            reference = execution_packets.get(work_unit_id)
            if (
                unit is None
                or not provider
                or decision.get("disposition") not in {
                    RoutingDisposition.DIRECT_OPENAI.value,
                    RoutingDisposition.OPENROUTER.value,
                    RoutingDisposition.CURSOR.value,
                    RoutingDisposition.LOCAL_QWEN.value,
                    RoutingDisposition.REMOTE_CPU_WORKER.value,
                }
                or work_unit_roles.get(work_unit_id) != ATOMIC_EXECUTABLE
                or not isinstance(reference, dict)
            ):
                continue
            packet_identity = str(reference.get("packet_sha256", ""))
            if not self._valid_sha256(packet_identity):
                continue
            # A source transition preserves prior-release packets so an in-flight
            # provider run can be polled and reconciled without duplicate paid
            # execution.  Its immutable pre-routing decision already belongs to
            # that prior release, however, and must never be rewritten using the
            # current release's route-identity policy.  Only a freshly generated
            # exact-current-base packet receives a new pre-routing decision.
            if reference.get("source_commit") != release_commit:
                continue
            route_identity = sha256_value(
                {
                    "provider": provider,
                    "model": decision.get("model"),
                    "task_format": unit.get("task_format"),
                    "schema_sha256": unit.get("schema_sha256"),
                    "packet_sha256": packet_identity,
                    "source_commit": reference.get("source_commit"),
                }
            )
            self.state.record_pre_routing_decision(
                decision={
                    "work_unit_id": work_unit_id,
                    "jira_identity": unit.get("jira_unit"),
                    "repository_identity": "KevinSGarrett/BatteredAggieSyndrome",
                    "source_commit": str(reference["source_commit"]),
                    "task_category": unit.get("task_format"),
                    "effort_points": int(unit.get("pre_routing_effort_points", 1)),
                    "candidate_routes": [str(provider)],
                    "selected_route": str(provider),
                    "route_identity": route_identity,
                    "budget_admission": (
                        "ZERO_COST_COMPUTE_ADMITTED"
                        if provider in {"remote_cpu_worker", "ollama_local"}
                        else "PROVIDER_BUDGET_ADMITTED"
                    ),
                    "packet_identity": packet_identity,
                    "lease_identity": None,
                    "disposition": "ROUTED_TO_ASSISTIVE_PLANE",
                    "reason_code": str(decision.get("reason", "EXACT_ROUTE_READY")),
                    "evidence_sha256": str(decision.get("work_unit_identity")),
                    "discovered_at": str(decision.get("decided_at")),
                },
                now=moment,
            )
        operational_demand = self._operational_demand(base, route_decisions, work_unit_roles)
        producer_watermarks = self._producer_watermarks(moment)
        active_conditions: set[str] = set()
        demand_evidence_sha256 = sha256_value(operational_demand)
        for provider in operational_demand.get("unmet_without_packets", []):
            condition_id = "PROVIDER_STARVATION:" + str(provider)
            active_conditions.add(condition_id)
            self.state.observe_operational_condition(
                condition_id=condition_id,
                finding="P0_PROVIDER_STARVATION:" + str(provider),
                threshold_seconds=1800,
                evidence_sha256=demand_evidence_sha256,
                now=moment,
            )
        for provider in operational_demand.get("empirically_suspended", []):
            condition_id = "USEFUL_WORK_GATE_FAILED:" + str(provider)
            active_conditions.add(condition_id)
            self.state.observe_operational_condition(
                condition_id=condition_id,
                finding="P0_PROVIDER_USEFUL_WORK_GATE_FAILED:" + str(provider),
                threshold_seconds=0,
                evidence_sha256=demand_evidence_sha256,
                now=moment,
            )
        for source_name, watermark in producer_watermarks.get("sources", {}).items():
            if watermark.get("scan_status") != "PASS":
                condition_id = "PRODUCER_SOURCE_SCAN_INCOMPLETE:" + str(source_name)
                active_conditions.add(condition_id)
                self.state.observe_operational_condition(
                    condition_id=condition_id,
                    finding=condition_id,
                    threshold_seconds=0,
                    evidence_sha256=str(watermark.get("watermark_identity")),
                    now=moment,
                )
        for finding in provider_work_findings:
            if finding.get("disposition") == "EXACT_PRODUCER_FAILED_UNRELATED_PRODUCERS_CONTINUE":
                condition_id = "WORK_PRODUCER_FAILED:" + str(finding.get("provider", "unknown"))
                active_conditions.add(condition_id)
                self.state.observe_operational_condition(
                    condition_id=condition_id,
                    finding="P0_AUTONOMOUS_WORK_PRODUCER_FAILED_WITH_DELEGABLE_WORK_PRESENT:"
                    + condition_id,
                    threshold_seconds=0,
                    evidence_sha256=sha256_value(finding),
                    now=moment,
                )
        self.state.resolve_operational_conditions(
            active_conditions,
            managed_prefixes=(
                "PROVIDER_STARVATION:",
                "PRODUCER_SOURCE_SCAN_INCOMPLETE:",
                "WORK_PRODUCER_FAILED:",
            ),
            now=moment,
        )
        inventory = ReadyWorkInventory(
            [
                ReadyWorkUnit(
                    **{
                        **{key: value for key, value in item.items() if key in READY_WORK_UNIT_FIELDS},
                        "source_hashes": tuple(item["source_hashes"]),
                        "dependencies": tuple(item["dependencies"]),
                    }
                )
                for item in work_units
            ],
            [
                RouteDecision(
                    **{
                        **{key: value for key, value in item.items() if key in ROUTE_DECISION_FIELDS},
                        "disposition": RoutingDisposition(item["disposition"]),
                    }
                )
                for item in route_decisions
            ],
        )
        validation = inventory.validate()
        role_validation = validate_work_unit_roles(inventory.units, work_unit_roles)
        static_base_identity = base.get(
            "static_base_inventory_identity",
            base.get("validation", {}).get("inventory_identity", base_sha256),
        )
        material_identity = sha256_value(
            {
                "base_inventory_identity": static_base_identity,
                "execution_packets": execution_packets,
                "execution_states": status,
                "route_decisions": route_decisions,
                "work_units": work_units,
                "work_unit_roles": work_unit_roles,
                "provider_work_findings": provider_work_findings,
                "continuous_packets": continuous_packets,
                "deployed_release": deployed_release,
                "external_evidence": live_external_evidence,
                "operational_demand": operational_demand,
                "producer_watermarks": producer_watermarks,
                "revision_supersessions": revision_supersessions,
            }
        )
        snapshot = {
            **{key: value for key, value in base.items() if key not in {"generated_at", "validation", "work_units", "work_unit_roles", "work_unit_role_validation", "route_decisions", "execution_packets", "runtime_material_identity", "provider_work_findings", "continuous_packets", "operational_demand", "producer_watermarks", "revision_supersessions", "git", "deployed_release"}},
            "schema_version": 2,
            "artifact_type": "UNIFIED_ASSISTIVE_RUNTIME_INVENTORY",
            "generated_at": rfc3339(moment),
            "runtime_material_identity": material_identity,
            "static_base_inventory_identity": static_base_identity,
            "work_units": work_units,
            "work_unit_roles": work_unit_roles,
            "work_unit_role_validation": role_validation,
            "route_decisions": route_decisions,
            "execution_packets": execution_packets,
            "execution_states": status,
            "provider_work_findings": provider_work_findings,
            "continuous_packets": continuous_packets,
            "operational_demand": operational_demand,
            "producer_watermarks": producer_watermarks,
            "revision_supersessions": revision_supersessions,
            "git": (
                {
                    "deployed_head": deployed_release["build_commit"],
                    "merged_main_identity_at_release_build": deployed_release["build_commit"],
                    "status_porcelain_sha256": hashlib.sha256(b"").hexdigest(),
                    "status_evidence": "IMMUTABLE_RELEASE_TREE_NO_WORKTREE_MUTATION_SURFACE",
                    "evidence_scope": deployed_release["evidence_scope"],
                }
                if deployed_release is not None
                else base.get("git")
            ),
            "deployed_release": deployed_release,
            "validation": validation,
            "canonical_or_protected_authority": False,
        }
        if base.get("runtime_material_identity") == material_identity:
            snapshot_sha256 = base_sha256
            snapshot_path = self.config.snapshot_root / "snapshots" / "sha256" / snapshot_sha256 / "inventory.json"
            if not snapshot_path.is_file():
                source = self.config.current_path
                current_payload = _verified_json(source)
                if current_payload.get("artifact_type") == "UNIFIED_ASSISTIVE_INVENTORY_POINTER":
                    source = Path(str(current_payload["snapshot_path"]))
                data = source.read_bytes()
                if hashlib.sha256(data).hexdigest() != snapshot_sha256:
                    raise RuntimeError("RUNTIME_INVENTORY_REUSE_HASH_MISMATCH")
                _atomic_write(snapshot_path, data)
        else:
            data = canonical_json_bytes(snapshot) + b"\n"
            snapshot_sha256 = hashlib.sha256(data).hexdigest()
            snapshot_path = self.config.snapshot_root / "snapshots" / "sha256" / snapshot_sha256 / "inventory.json"
            if snapshot_path.exists():
                if snapshot_path.read_bytes() != data:
                    raise RuntimeError("RUNTIME_INVENTORY_SNAPSHOT_COLLISION")
            else:
                _atomic_write(snapshot_path, data)
        pointer = {
            "schema_version": 2,
            "artifact_type": "UNIFIED_ASSISTIVE_INVENTORY_POINTER",
            "snapshot_path": str(snapshot_path),
            "snapshot_sha256": snapshot_sha256,
            "inventory_identity": validation["inventory_identity"],
            "runtime_material_identity": material_identity,
            "refreshed_at": rfc3339(moment),
        }
        _atomic_write(self.config.current_path, canonical_json_bytes(pointer) + b"\n")
        return {
            "result": "PASS",
            "snapshot_path": str(snapshot_path),
            "snapshot_sha256": snapshot_sha256,
            "inventory_identity": validation["inventory_identity"],
            "runtime_material_identity": material_identity,
            "granular_units": len(prior_units),
            "refreshed_at": pointer["refreshed_at"],
        }

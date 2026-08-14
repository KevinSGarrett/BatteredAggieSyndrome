from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from aggie_analytics.openai_assist.contracts import Priority, sha256_value
from aggie_analytics.openai_assist.controller import AssistiveController, AssistiveJob

from .contracts import AssistiveRequest, Authority, Disposition, sha256_value as plane_sha256_value
from .budget import BudgetLedger
from .cursor_backend import (
    CursorApiError,
    CursorBackend,
    CursorCloudClient,
    CursorRunPolicy,
    cursor_agent_identity,
)
from .dispatcher import AssistiveDispatcher
from .openrouter_backend import OpenRouterBackend
from .ollama_backend import OLLAMA_LOOPBACK_ENDPOINT
from .orchestration import write_content_addressed_json


BGE_MODEL = "bge-m3:latest"
BGE_MODEL_DIGEST = "7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab"
BGE_TASK_FORMAT = "embedding_dedup_semantic_candidate_retrieval"
BGE_POLICY_VERSION = "unified-assistive-execution-plane-v2-operational-correction"
BGE_PROMPT_VERSION = "embedding-shadow-v1"
BGE_SCHEMA_VERSION = "1"
BGE_SCHEMA_SHA256 = "fd5ed573e9990a40674b28032a2b4fb63659c62423479c554188149826ea362c"
OPENROUTER_TASK_FORMAT = "governed_openrouter_candidate_v1"
CURSOR_TASK_FORMAT = "governed_cursor_repository_review_v1"
CURSOR_IMPLEMENTATION_TASK_FORMAT = "governed_cursor_repository_implementation_v1"
CURSOR_TASK_FORMATS = frozenset(
    {CURSOR_TASK_FORMAT, CURSOR_IMPLEMENTATION_TASK_FORMAT}
)
MAX_CURSOR_CHANGED_FILES = 32
MAX_CURSOR_DIFF_BYTES = 2 * 1024 * 1024


class CursorCandidateValidationError(RuntimeError):
    """Terminal, unit-scoped rejection of a Cursor candidate branch."""


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


def _cursor_branch(run: dict[str, Any]) -> str | None:
    git = run.get("git")
    if not isinstance(git, dict):
        return None
    branch = git.get("branchName")
    if isinstance(branch, str) and branch:
        return branch
    branches = git.get("branches")
    if not isinstance(branches, list) or len(branches) != 1:
        return None
    item = branches[0]
    if not isinstance(item, dict) or not isinstance(item.get("branch"), str):
        return None
    return str(item["branch"])


def inspect_cursor_candidate_branch(
    packet: dict[str, Any], branch: str
) -> dict[str, Any]:
    repository_url = str(packet.get("repository_url", ""))
    expected = "https://github.com/KevinSGarrett/BatteredAggieSyndrome.git"
    if repository_url != expected:
        raise CursorCandidateValidationError(
            "CURSOR_IMPLEMENTATION_REPOSITORY_NOT_ADMITTED"
        )
    allowed_paths = packet.get("allowed_paths")
    if (
        not isinstance(allowed_paths, list)
        or not allowed_paths
        or any(not _safe_cursor_repository_path(path) for path in allowed_paths)
    ):
        raise CursorCandidateValidationError(
            "CURSOR_IMPLEMENTATION_ALLOWED_PATHS_INVALID"
        )
    base_commit = str(packet.get("base_commit", ""))
    encoded_branch = urllib.parse.quote(branch, safe="")
    endpoint = (
        "https://api.github.com/repos/KevinSGarrett/BatteredAggieSyndrome/compare/"
        f"{base_commit}...{encoded_branch}"
    )
    request = urllib.request.Request(
        endpoint,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "BAS-UnifiedAssistiveController/1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        comparison = json.loads(response.read().decode("utf-8"))
    files = comparison.get("files")
    if (
        not isinstance(files, list)
        or not files
        or len(files) > MAX_CURSOR_CHANGED_FILES
        or len(files) >= 300
    ):
        raise CursorCandidateValidationError(
            "CURSOR_IMPLEMENTATION_CHANGED_FILE_SET_INVALID"
        )
    merge_base = comparison.get("merge_base_commit")
    if not isinstance(merge_base, dict) or merge_base.get("sha") != base_commit:
        raise CursorCandidateValidationError(
            "CURSOR_IMPLEMENTATION_BASE_COMMIT_MISMATCH"
        )
    changed_paths = sorted(
        str(item.get("filename")) for item in files if isinstance(item, dict)
    )
    if len(changed_paths) != len(files) or any(
        not _safe_cursor_repository_path(path) for path in changed_paths
    ):
        raise CursorCandidateValidationError(
            "CURSOR_IMPLEMENTATION_CHANGED_PATH_INVALID"
        )

    def allowed(path: str) -> bool:
        return any(
            path == permitted
            or (permitted.endswith("/") and path.startswith(permitted))
            for permitted in allowed_paths
        )

    unauthorized = [path for path in changed_paths if not allowed(path)]
    if unauthorized:
        raise CursorCandidateValidationError(
            "CURSOR_IMPLEMENTATION_PATH_NOT_ALLOWED:" + ",".join(unauthorized)
        )
    diff_request = urllib.request.Request(
        endpoint,
        headers={
            "Accept": "application/vnd.github.v3.diff",
            "User-Agent": "BAS-UnifiedAssistiveController/1",
        },
    )
    with urllib.request.urlopen(diff_request, timeout=30) as response:
        diff = response.read(MAX_CURSOR_DIFF_BYTES + 1)
    if not diff or len(diff) > MAX_CURSOR_DIFF_BYTES:
        raise CursorCandidateValidationError(
            "CURSOR_IMPLEMENTATION_DIFF_SIZE_INVALID"
        )
    head = comparison.get("head_commit")
    if not isinstance(head, dict) or not isinstance(head.get("sha"), str):
        raise CursorCandidateValidationError(
            "CURSOR_IMPLEMENTATION_HEAD_COMMIT_MISSING"
        )
    return {
        "schema_version": 1,
        "artifact_type": "CURSOR_CANDIDATE_BRANCH_VALIDATION",
        "authority": "CANDIDATE_ONLY",
        "repository_url": repository_url,
        "base_commit": base_commit,
        "head_commit": str(head["sha"]),
        "branch": branch,
        "changed_paths": changed_paths,
        "allowed_paths": sorted(allowed_paths),
        "diff_sha256": hashlib.sha256(diff).hexdigest(),
        "diff_bytes": len(diff),
        "diff_text": diff.decode("utf-8", errors="replace"),
        "comparison_url": str(comparison.get("html_url", "")),
        "canonical_writes": 0,
        "protected_decisions": 0,
    }


class _CountingBackend:
    """Count every provider submission, including failed and retried calls."""

    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.name = delegate.name
        self.calls = 0

    def submit(self, request: AssistiveRequest, schema: dict[str, object]) -> Any:
        self.calls += 1
        return self.delegate.submit(request, schema)


@dataclass(frozen=True)
class ProviderAdapterResult:
    remote_identity: str
    result: dict[str, Any]
    disposition: str
    validation_errors: tuple[str, ...]
    actual_cost_usd: str
    resource: dict[str, Any]


class BgeM3CandidateAdapter:
    """Exact-route local semantic retrieval; never an authority-bearing writer."""

    def __init__(
        self,
        endpoint: str = OLLAMA_LOOPBACK_ENDPOINT,
        *,
        transport: Callable[[str, dict[str, Any] | None], dict[str, Any]] | None = None,
    ) -> None:
        if endpoint.rstrip("/") != OLLAMA_LOOPBACK_ENDPOINT:
            raise ValueError("BGE_ADAPTER_REQUIRES_LOOPBACK_OLLAMA")
        self.endpoint = endpoint.rstrip("/")
        self.transport = transport or self._http

    def _http(self, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint + path,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="GET" if body is None else "POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read())
        if not isinstance(result, dict):
            raise RuntimeError("BGE_OLLAMA_RESPONSE_NOT_OBJECT")
        return result

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if len(left) != len(right) or not left:
            raise RuntimeError("BGE_EMBEDDING_DIMENSION_INVALID")
        numerator = sum(a * b for a, b in zip(left, right))
        denominator = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
        if denominator == 0:
            raise RuntimeError("BGE_ZERO_NORM_EMBEDDING")
        return numerator / denominator

    def run(self, packet: dict[str, Any]) -> ProviderAdapterResult:
        required = {
            "task_format": BGE_TASK_FORMAT,
            "model": BGE_MODEL,
            "model_digest": BGE_MODEL_DIGEST,
            "policy_version": BGE_POLICY_VERSION,
            "prompt_version": BGE_PROMPT_VERSION,
            "route_schema_version": BGE_SCHEMA_VERSION,
            "schema_sha256": BGE_SCHEMA_SHA256,
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
        }
        for key, expected in required.items():
            if packet.get(key) != expected:
                raise RuntimeError(f"BGE_EXACT_ROUTE_IDENTITY_MISMATCH:{key}")
        query = packet.get("query")
        candidates = packet.get("candidates")
        if not isinstance(query, str) or not query.strip() or not isinstance(candidates, list):
            raise RuntimeError("BGE_RETRIEVAL_INPUT_INVALID")
        if not 1 <= len(candidates) <= 256:
            raise RuntimeError("BGE_RETRIEVAL_CANDIDATE_BOUND_INVALID")
        candidate_ids: list[str] = []
        texts: list[str] = []
        for item in candidates:
            if not isinstance(item, dict) or not isinstance(item.get("candidate_id"), str) or not isinstance(item.get("text"), str):
                raise RuntimeError("BGE_RETRIEVAL_CANDIDATE_INVALID")
            candidate_ids.append(item["candidate_id"])
            texts.append(item["text"])
        if len(set(candidate_ids)) != len(candidate_ids):
            raise RuntimeError("BGE_RETRIEVAL_CANDIDATE_ID_DUPLICATE")
        tags = self.transport("/api/tags", None)
        matches = [item for item in tags.get("models", []) if item.get("name") == BGE_MODEL]
        if len(matches) != 1 or matches[0].get("digest") != BGE_MODEL_DIGEST:
            raise RuntimeError("BGE_LIVE_MODEL_DIGEST_NOT_QUALIFIED")
        embedded = self.transport("/api/embed", {"model": BGE_MODEL, "input": [query, *texts]})
        vectors = embedded.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts) + 1:
            raise RuntimeError("BGE_EMBEDDING_COUNT_INVALID")
        scores = sorted(
            (
                {"candidate_id": candidate_id, "score": round(self._cosine(vectors[0], vector), 12)}
                for candidate_id, vector in zip(candidate_ids, vectors[1:])
            ),
            key=lambda item: (-item["score"], item["candidate_id"]),
        )
        result = {
            "schema_version": 1,
            "artifact_type": "BGE_M3_CANDIDATE_RETRIEVAL",
            "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "rankings": scores,
            "model": BGE_MODEL,
            "model_digest": BGE_MODEL_DIGEST,
            "task_format": BGE_TASK_FORMAT,
            "authority": "CANDIDATE_ONLY",
            "canonical_writes": 0,
            "protected_decisions": 0,
        }
        return ProviderAdapterResult(
            remote_identity=f"{BGE_MODEL}@sha256:{BGE_MODEL_DIGEST}",
            result=result,
            disposition="REVIEW_ONLY",
            validation_errors=(),
            actual_cost_usd="0.000000",
            resource={"candidate_count": len(candidates), "embedding_count": len(vectors), "provider_calls": 1},
        )


class GovernedOpenAIAdapter:
    """Thin scheduler bridge to the project's single governed OpenAI controller."""

    def __init__(self, release_root: Path, *, client_factory: Callable[[str], Any] | None = None) -> None:
        self.release_root = release_root.resolve()
        self.controller = AssistiveController(self.release_root, client_factory=client_factory)

    def run(self, packet: dict[str, Any]) -> ProviderAdapterResult:
        if packet.get("task_format") != "governed_openai_candidate_v1":
            raise RuntimeError("OPENAI_TASK_FORMAT_NOT_ADMITTED")
        if packet.get("authority") != "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES":
            raise RuntimeError("OPENAI_PACKET_AUTHORITY_INVALID")
        job_value = packet.get("job")
        if not isinstance(job_value, dict):
            raise RuntimeError("OPENAI_JOB_NOT_OBJECT")
        allowed_fields = set(AssistiveJob.__dataclass_fields__)
        if set(job_value) - allowed_fields:
            raise RuntimeError("OPENAI_JOB_UNKNOWN_FIELDS")
        values = dict(job_value)
        values["schema_path"] = self.release_root / str(values["schema_path"])
        schema = self.controller._load_schema(values["schema_path"])
        if packet.get("schema_sha256") != sha256_value(schema):
            raise RuntimeError("OPENAI_PACKET_SCHEMA_IDENTITY_MISMATCH")
        if values.get("source_capture_sha256") not in packet.get("source_hashes", []):
            raise RuntimeError("OPENAI_SOURCE_CAPTURE_NOT_BOUND_TO_WORK_UNIT")
        values["priority"] = Priority(str(values.get("priority", "NORMAL")))
        if values.get("source_image_path"):
            values["source_image_path"] = Path(str(values["source_image_path"]))
        result = self.controller.run_sync(AssistiveJob(**values))
        payload = {
            "request_id": result.request_id,
            "disposition": result.disposition,
            "candidate": result.candidate,
            "validation_errors": list(result.validation_errors),
            "response_sha256": result.response_sha256,
            "actual_cost_usd": result.actual_cost_usd,
            "cached": result.cached,
            "authority": "CANDIDATE_ONLY",
            "canonical_writes": 0,
            "protected_decisions": 0,
        }
        disposition = result.disposition if result.disposition in {"QUARANTINE", "REJECTED"} else "REVIEW_ONLY"
        return ProviderAdapterResult(
            remote_identity=result.request_id,
            result=payload,
            disposition=disposition,
            validation_errors=result.validation_errors,
            actual_cost_usd=result.actual_cost_usd,
            resource={
                "cached": result.cached,
                "model": values["model"],
                "reasoning_effort": values["reasoning_effort"],
                "provider_calls": 0 if result.cached else 1,
            },
        )


class GovernedOpenRouterAdapter:
    """Scheduler bridge that reuses the governed OpenRouter dispatcher/policy stack."""

    def __init__(
        self,
        root: Path,
        *,
        policy_path: Path | None = None,
        backend_factory: Callable[[Path], Any] | None = None,
        dispatcher_factory: Callable[[Path, Any, Path], Any] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.policy_path = (policy_path or (self.root / "configs" / "openrouter_assist_policy.json")).resolve()
        policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        env_path = Path(str(policy["credential"]["authoritative_env"]))
        backend = (backend_factory or OpenRouterBackend)(env_path)
        self.backend = _CountingBackend(backend)
        self.dispatcher = (dispatcher_factory or AssistiveDispatcher)(self.root, self.backend, self.policy_path)
        self.task_registry = json.loads((self.root / "configs" / "openrouter_task_registry.json").read_text(encoding="utf-8"))

    @staticmethod
    def _valid_sha256(value: object) -> bool:
        text = str(value)
        return len(text) == 64 and all(character in "0123456789abcdef" for character in text)

    def run(self, packet: dict[str, Any]) -> ProviderAdapterResult:
        if packet.get("provider") != "openrouter" or packet.get("task_format") != OPENROUTER_TASK_FORMAT:
            raise RuntimeError("OPENROUTER_TASK_FORMAT_NOT_ADMITTED")
        if packet.get("authority") != "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES":
            raise RuntimeError("OPENROUTER_PACKET_AUTHORITY_INVALID")
        source_hashes = packet.get("source_hashes")
        if not isinstance(source_hashes, list) or not source_hashes or not all(self._valid_sha256(item) for item in source_hashes):
            raise RuntimeError("OPENROUTER_SOURCE_HASHES_INVALID")
        identity_hashes = packet.get("identity_hashes")
        if not isinstance(identity_hashes, dict):
            raise RuntimeError("OPENROUTER_IDENTITY_HASHES_MISSING")
        expected_hashes = {
            "task_sha256": plane_sha256_value(
                {
                    "task_id": packet.get("task_id"),
                    "jira_unit": packet.get("jira_unit"),
                    "authority": packet.get("authority"),
                }
            ),
            "schema_sha256": plane_sha256_value(
                {"schema_version": packet.get("request_schema_version"), "schema_sha256": packet.get("schema_sha256")}
            ),
            "policy_sha256": plane_sha256_value(
                {
                    "provider_policy_version": packet.get("provider_policy_version"),
                    "task_format": packet.get("task_format"),
                }
            ),
            "model_sha256": plane_sha256_value({"model": packet.get("model")}),
            "reasoning_sha256": plane_sha256_value(
                {
                    "reasoning_effort": packet.get("reasoning_effort"),
                    "max_output_tokens": packet.get("max_output_tokens"),
                }
            ),
            "source_sha256": plane_sha256_value(tuple(source_hashes)),
        }
        if identity_hashes != expected_hashes:
            raise RuntimeError("OPENROUTER_IDENTITY_HASH_MISMATCH")
        task = self.task_registry.get("tasks", {}).get(packet.get("task_id"))
        if not isinstance(task, dict):
            raise RuntimeError("OPENROUTER_TASK_NOT_REGISTERED")
        schema = json.loads((self.root / str(task["schema"])).read_text(encoding="utf-8"))
        request = AssistiveRequest(
            task_id=str(packet["task_id"]),
            jira_unit=str(packet["jira_unit"]),
            base_commit=str(packet["base_commit"]),
            authority=Authority(str(task["authority"])),
            prompt_version=str(packet["prompt_version"]),
            schema_version=str(packet["request_schema_version"]),
            schema_sha256=str(packet["schema_sha256"]),
            source_hashes=tuple(str(item) for item in source_hashes),
            evidence_excerpts=tuple(str(item) for item in packet.get("evidence_excerpts", [])),
            model=str(packet["model"]),
            reasoning_effort=str(packet["reasoning_effort"]),
            max_output_tokens=int(packet["max_output_tokens"]),
            provider_policy_version=str(packet["provider_policy_version"]),
        )
        calls_before = self.backend.calls
        result = self.dispatcher.dispatch(request, schema)
        provider_calls = self.backend.calls - calls_before
        provider_result = result.provider_result
        payload = {
            "request_id": result.request_id,
            "disposition": result.disposition.value,
            "reason": result.reason,
            "manifest_path": result.manifest_path,
            "provider_result": (
                {
                    "provider": provider_result.provider,
                    "model_requested": provider_result.model_requested,
                    "model_resolved": provider_result.model_resolved,
                    "usage": provider_result.usage,
                    "raw_response_id": provider_result.raw_response_id,
                    "cost_usd": provider_result.cost_usd,
                    "output": provider_result.output,
                }
                if provider_result is not None
                else None
            ),
            "authority": "CANDIDATE_ONLY",
            "canonical_writes": 0,
            "protected_decisions": 0,
        }
        if result.disposition is Disposition.QUARANTINE:
            scheduler_disposition = "QUARANTINE"
        elif result.disposition is Disposition.REJECTED:
            scheduler_disposition = "REJECTED"
        else:
            scheduler_disposition = "REVIEW_ONLY"
        actual_cost = (
            str(provider_result.cost_usd)
            if provider_result is not None and provider_result.cost_usd is not None
            else "0.000000"
        )
        return ProviderAdapterResult(
            remote_identity=result.request_id,
            result=payload,
            disposition=scheduler_disposition,
            validation_errors=() if scheduler_disposition == "REVIEW_ONLY" else (result.reason,),
            actual_cost_usd=actual_cost,
            resource={
                "provider_calls": provider_calls,
                "cached": result.reason == "CACHE_HIT",
                "manifest_path": result.manifest_path,
                "openrouter_disposition": result.disposition.value,
                "reasoning_effort": request.reasoning_effort,
                "model": request.model,
            },
        )


class GovernedCursorAdapter:
    """Durable submit/poll bridge for exact-base candidate-only Cursor agents."""

    TERMINAL = frozenset({"FINISHED", "ERROR", "CANCELLED", "EXPIRED"})

    def __init__(
        self,
        root: Path,
        *,
        client: CursorCloudClient | None = None,
        store_root: Path = Path(r"C:\BatteredAggieSyndrome.data\assistive\cursor"),
        branch_inspector: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.store_root = store_root
        policy = json.loads((self.root / "configs" / "unified_assistive_policy.json").read_text(encoding="utf-8"))
        budget = policy["budgets"]["cursor"]
        self.ledger = BudgetLedger(
            self.store_root / "usage" / "ledger.json",
            Decimal(str(budget["hard_limit_usd"])),
            Decimal(str(budget["released_stage_usd"])),
        )
        env_path = Path(
            os.environ.get("AGGIE_AUTHORITATIVE_ENV_PATH", r"C:\BatteredAggieSyndrome\.env")
        )
        self.client = client or CursorCloudClient(env_path)
        self.branch_inspector = branch_inspector or inspect_cursor_candidate_branch

    @staticmethod
    def _job_identity(packet: dict[str, Any]) -> str:
        return plane_sha256_value(
            {
                "jira_unit": packet.get("jira_unit"),
                "prompt": packet.get("prompt"),
                "repository_url": packet.get("repository_url"),
                "starting_ref": packet.get("starting_ref"),
                "base_commit": packet.get("base_commit"),
                "model": packet.get("model"),
                "reasoning": packet.get("reasoning"),
                "task_format": packet.get("task_format"),
                "schema_sha256": packet.get("schema_sha256"),
            }
        )

    def submit(self, packet: dict[str, Any]) -> dict[str, Any]:
        if (
            packet.get("provider") != "cursor"
            or packet.get("task_format") not in CURSOR_TASK_FORMATS
        ):
            raise RuntimeError("CURSOR_TASK_FORMAT_NOT_ADMITTED")
        if packet.get("authority") != "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES":
            raise RuntimeError("CURSOR_PACKET_AUTHORITY_INVALID")
        backend = CursorBackend(
            CursorRunPolicy(model=str(packet["model"]), reasoning=str(packet["reasoning"]))
        )
        job_id = self._job_identity(packet)
        agent_id = cursor_agent_identity(job_id)
        reservation = Decimal(str(packet["max_reservation_usd"]))
        settled_amount = self.ledger.settled_amount(job_id)
        if settled_amount is not None:
            response = {
                "idempotent_settled_recovery": True,
                "settled_usd": format(settled_amount, "f"),
            }
        else:
            self.ledger.reserve(job_id, reservation)
        payload = backend.build_create_payload(
            prompt=str(packet["prompt"]),
            repository_url=str(packet["repository_url"]),
            starting_ref=str(packet["starting_ref"]),
            agent_id=agent_id,
        )
        if settled_amount is None:
            try:
                response = self.client.request("POST", "/agents", payload)
            except CursorApiError as exc:
                if exc.status != 409 or exc.code != "agent_id_conflict":
                    self.ledger.release(job_id)
                    raise
                response = {
                    "agent": self.client.request("GET", f"/agents/{agent_id}"),
                    "idempotent_conflict_recovery": True,
                }
        evidence = {
            "schema_version": 1,
            "artifact_type": "CURSOR_CONTROLLER_ROUTED_SUBMISSION",
            "job_id": job_id,
            "agent_id": agent_id,
            "jira_unit": packet["jira_unit"],
            "base_commit": packet["base_commit"],
            "model": backend.policy.model,
            "reasoning": backend.policy.reasoning,
            "fast": False,
            "work_on_current_branch": False,
            "auto_create_pr": False,
            "reservation_usd": format(reservation, "f"),
            "prompt_sha256": hashlib.sha256(str(packet["prompt"]).encode("utf-8")).hexdigest(),
            "response": response,
            "dispatch_origin": "PERSISTENT_CONTROLLER",
            "candidate_only": True,
            "idempotent_settled_recovery": settled_amount is not None,
        }
        path, digest = write_content_addressed_json(self.store_root, "controller_requests", evidence)
        return {
            "job_id": job_id,
            "agent_id": agent_id,
            "request_path": str(path),
            "request_sha256": digest,
            "provider_calls": 0 if settled_amount is not None else 1,
            "idempotent_settled_recovery": settled_amount is not None,
        }

    def poll(self, packet: dict[str, Any], handle: dict[str, Any]) -> ProviderAdapterResult | None:
        job_id = self._job_identity(packet)
        agent_id = cursor_agent_identity(job_id)
        if handle.get("job_id") != job_id or handle.get("agent_id") != agent_id:
            raise RuntimeError("CURSOR_DURABLE_HANDLE_IDENTITY_MISMATCH")
        agent = self.client.request("GET", f"/agents/{agent_id}")
        run_id = str(agent.get("latestRunId", ""))
        if not run_id:
            return None
        run = self.client.request("GET", f"/agents/{agent_id}/runs/{run_id}")
        status = str(run.get("status", ""))
        if status not in self.TERMINAL:
            return None
        usage = self.client.request("GET", f"/agents/{agent_id}/usage")
        cost = usage.get("cost", {})
        charged_cents = cost.get("chargedCents") if isinstance(cost, dict) else None
        if charged_cents is None:
            raise RuntimeError("CURSOR_TERMINAL_USAGE_COST_MISSING")
        actual = Decimal(str(charged_cents)) / Decimal("100")
        self.ledger.settle(job_id, actual)
        branch = _cursor_branch(run)
        candidate_validation: dict[str, Any] | None = None
        candidate_validation_path: Path | None = None
        candidate_validation_sha256: str | None = None
        validation_errors: list[str] = []
        if (
            packet.get("task_format") == CURSOR_IMPLEMENTATION_TASK_FORMAT
            and status == "FINISHED"
        ):
            if branch is None:
                validation_errors.append("CURSOR_IMPLEMENTATION_BRANCH_MISSING")
            else:
                try:
                    candidate_validation = self.branch_inspector(packet, branch)
                except CursorCandidateValidationError as exc:
                    validation_errors.append(str(exc))
                except urllib.error.HTTPError as exc:
                    # A terminal Cursor run can report a branch name while no
                    # corresponding remote ref exists.  GitHub represents that
                    # no-candidate outcome as a compare 404.  Retrying it forever
                    # keeps the paid run leased and prevents settlement, so close
                    # only this unit as rejected.  Other HTTP failures remain
                    # retryable at the scheduler boundary.
                    if exc.code != 404:
                        exc.close()
                        raise
                    validation_errors.append(
                        "CURSOR_IMPLEMENTATION_REMOTE_BRANCH_NOT_FOUND"
                    )
                    exc.close()
                if candidate_validation is not None:
                    changed_paths = candidate_validation.get("changed_paths")
                    allowed_paths = packet.get("allowed_paths")

                    def permitted(path: str) -> bool:
                        return isinstance(allowed_paths, list) and any(
                            path == allowed
                            or (
                                isinstance(allowed, str)
                                and allowed.endswith("/")
                                and path.startswith(allowed)
                            )
                            for allowed in allowed_paths
                        )

                    if (
                        candidate_validation.get("authority") != "CANDIDATE_ONLY"
                        or candidate_validation.get("base_commit")
                        != packet.get("base_commit")
                        or candidate_validation.get("canonical_writes") != 0
                        or candidate_validation.get("protected_decisions") != 0
                        or not isinstance(changed_paths, list)
                        or not changed_paths
                        or any(
                            not isinstance(path, str) or not permitted(path)
                            for path in changed_paths
                        )
                        or not isinstance(candidate_validation.get("head_commit"), str)
                        or len(str(candidate_validation.get("head_commit"))) != 40
                        or not isinstance(candidate_validation.get("diff_sha256"), str)
                        or len(str(candidate_validation.get("diff_sha256"))) != 64
                        or int(candidate_validation.get("diff_bytes", 0)) <= 0
                    ):
                        validation_errors.append(
                            "CURSOR_IMPLEMENTATION_VALIDATION_AUTHORITY_INVALID"
                        )
                        candidate_validation = None
                if candidate_validation is not None:
                    candidate_validation_path, candidate_validation_sha256 = (
                        write_content_addressed_json(
                            self.store_root,
                            "candidate_branch_validations",
                            candidate_validation,
                        )
                    )
        if status != "FINISHED":
            validation_errors.append(f"CURSOR_RUN_{status}")
        result = {
            "schema_version": 1,
            "artifact_type": "CURSOR_CONTROLLER_ROUTED_CANDIDATE_RESULT",
            "job_id": job_id,
            "agent_id": agent_id,
            "run_id": run_id,
            "status": status,
            "agent": agent,
            "run": run,
            "usage": usage,
            "git": run.get("git", {}),
            "dispatch_origin": "PERSISTENT_CONTROLLER",
            "authority": "CANDIDATE_ONLY",
            "canonical_writes": 0,
            "protected_decisions": 0,
            "candidate_validation_path": (
                str(candidate_validation_path) if candidate_validation_path else None
            ),
            "candidate_validation_sha256": candidate_validation_sha256,
        }
        path, digest = write_content_addressed_json(self.store_root, "controller_results", result)
        disposition = "REVIEW_ONLY" if not validation_errors else "REJECTED"
        return ProviderAdapterResult(
            remote_identity=f"{agent_id}:{run_id}",
            result={**result, "artifact_path": str(path), "artifact_sha256": digest},
            disposition=disposition,
            validation_errors=tuple(validation_errors),
            actual_cost_usd=format(actual, "f"),
            resource={
                "provider_calls": 0,
                "agent_id": agent_id,
                "run_id": run_id,
                "job_id": job_id,
                "branch": branch,
                "candidate_validation_path": (
                    str(candidate_validation_path) if candidate_validation_path else None
                ),
                "candidate_validation_sha256": candidate_validation_sha256,
                "changed_paths": (
                    candidate_validation.get("changed_paths", [])
                    if candidate_validation
                    else []
                ),
                "model": packet["model"],
                "reasoning": packet["reasoning"],
            },
        )

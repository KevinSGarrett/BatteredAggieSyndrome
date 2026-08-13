from __future__ import annotations

import hashlib
import json
import math
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from aggie_analytics.openai_assist.contracts import Priority, sha256_value
from aggie_analytics.openai_assist.controller import AssistiveController, AssistiveJob

from .contracts import AssistiveRequest, Authority, Disposition, sha256_value as plane_sha256_value
from .dispatcher import AssistiveDispatcher
from .openrouter_backend import OpenRouterBackend
from .ollama_backend import OLLAMA_LOOPBACK_ENDPOINT


BGE_MODEL = "bge-m3:latest"
BGE_MODEL_DIGEST = "7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab"
BGE_TASK_FORMAT = "embedding_dedup_semantic_candidate_retrieval"
BGE_POLICY_VERSION = "unified-assistive-execution-plane-v2-operational-correction"
BGE_PROMPT_VERSION = "embedding-shadow-v1"
BGE_SCHEMA_VERSION = "1"
BGE_SCHEMA_SHA256 = "fd5ed573e9990a40674b28032a2b4fb63659c62423479c554188149826ea362c"
OPENROUTER_TASK_FORMAT = "governed_openrouter_candidate_v1"


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
        self.dispatcher = (dispatcher_factory or AssistiveDispatcher)(self.root, backend, self.policy_path)
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
        result = self.dispatcher.dispatch(request, schema)
        provider_result = result.provider_result
        provider_calls = 0
        if provider_result is not None and result.reason != "CACHE_HIT":
            provider_calls = 1
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

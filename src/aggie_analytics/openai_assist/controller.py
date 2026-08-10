from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from .budget import BudgetError, Reservation, UsageLedger
from .contracts import Priority, ProcessingMode, TokenEstimate, canonical_json_bytes, money, sha256_value
from .credentials import configured_secret_values, key_is_nonempty, load_openai_api_key
from .policy import AssistivePolicy, PolicyError
from .redaction import assert_prompt_safe
from .schemas import evidence_errors, validate_instance, validate_strict_output_schema
from .storage import ExternalStore


class ControllerError(RuntimeError):
    pass


@dataclass(frozen=True)
class AssistiveJob:
    task_name: str
    jira_unit: str
    source_url: str
    source_capture_sha256: str
    source_excerpt: str
    prompt: str
    prompt_version: str
    schema_path: Path
    schema_version: str
    model: str
    reasoning_effort: str
    allocation: str
    destination: str
    max_output_tokens: int = 2048
    priority: Priority = Priority.NORMAL
    release_reason: str | None = None
    admission_review_id: str | None = None


@dataclass(frozen=True)
class AssistiveResult:
    request_id: str
    disposition: str
    candidate: dict[str, Any] | None
    validation_errors: tuple[str, ...]
    response_sha256: str
    actual_cost_usd: str
    cached: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _object_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise ControllerError("OpenAI SDK returned an unsupported response object")


def _usage_dict(response: dict[str, Any]) -> dict[str, int]:
    usage = response.get("usage") or {}
    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}
    return {
        "input_tokens": int(usage.get("input_tokens") or 0),
        "cached_input_tokens": int(input_details.get("cached_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "reasoning_tokens": int(output_details.get("reasoning_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
    }


def _output_text(response: dict[str, Any]) -> str:
    pieces: list[str] = []
    for item in response.get("output") or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if content.get("type") == "output_text":
                pieces.append(str(content.get("text", "")))
            elif content.get("type") == "refusal":
                raise ControllerError("model refused the governed extraction request")
    return "".join(pieces)


class AssistiveController:
    def __init__(
        self,
        repo_root: Path,
        *,
        client_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.policy = AssistivePolicy.load(self.repo_root)
        self.registry = json.loads(
            (self.repo_root / "configs" / "openai_task_registry.json").read_text(encoding="utf-8")
        )
        self.store = ExternalStore(
            self.policy.storage_root,
            list(self.policy.payload["storage"]["subdirectories"]),
        )
        self.store.initialize()
        self.ledger = UsageLedger(self.policy, self.store.directory("usage"))
        self._client_factory = client_factory

    def doctor(self) -> dict[str, Any]:
        schema = self._load_schema(self.repo_root / "schemas" / "openai" / "assistive_candidate.schema.json")
        validate_strict_output_schema(schema)
        return {
            "result": "PASS",
            "api_key_nonempty": key_is_nonempty(self.repo_root),
            "policy_id": self.policy.payload["policy_id"],
            "storage_root": str(self.store.root),
            "storage_outside_git": True,
            "store": self.policy.payload["api"]["store"],
            "budget": self.ledger.summary(),
        }

    def _client(self) -> Any:
        key = load_openai_api_key(self.repo_root)
        if self._client_factory is not None:
            return self._client_factory(key)
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ControllerError(
                "install the hash-locked 'openai-assist' optional dependency"
            ) from exc
        return OpenAI(api_key=key, max_retries=0)

    @staticmethod
    def _load_schema(path: Path) -> dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        validate_strict_output_schema(value)
        return value

    def _task(self, job: AssistiveJob) -> dict[str, Any]:
        tasks = self.registry.get("tasks", {})
        if job.task_name not in tasks:
            raise ControllerError(f"unregistered assistive task: {job.task_name}")
        task = tasks[job.task_name]
        if task["jira_unit"] != job.jira_unit:
            raise ControllerError("job Jira identity disagrees with the task registry")
        if task["candidate_destination"] != job.destination:
            raise ControllerError("job destination disagrees with the task registry")
        return task

    def _validate_job(self, job: AssistiveJob, schema: dict[str, Any]) -> None:
        task = self._task(job)
        self._schema_reference(job.schema_path)
        self.policy.validate_route(job.model, job.reasoning_effort)
        if job.model not in set(task.get("allowed_models", [])):
            raise ControllerError("job model is outside the task-specific router")
        allocation_by_model = task.get("allocation_by_model", {})
        expected_allocation = allocation_by_model.get(job.model)
        if expected_allocation != job.allocation and job.allocation != "VALUE_GATED_RESERVE":
            raise ControllerError("job allocation disagrees with the task/model router")
        allowed = set(self.policy.payload["authority"]["allowed_destinations"])
        if job.destination not in allowed:
            raise ControllerError("job destination is outside the candidate-only authority boundary")
        if job.max_output_tokens <= 0 or job.max_output_tokens > 128_000:
            raise ControllerError("max_output_tokens is outside the governed range")
        if len(job.source_capture_sha256) != 64 or any(c not in "0123456789abcdef" for c in job.source_capture_sha256):
            raise ControllerError("source capture identity must be lowercase SHA-256")
        if not job.source_url.startswith(("http://", "https://", "file:")):
            raise ControllerError("source URL must be an explicit public or local evidence locator")
        if task.get("conditional"):
            raise ControllerError("conditional task has not been explicitly activated by evidence readiness")
        validate_strict_output_schema(schema)
        assert_prompt_safe(asdict(job))

    def _configured_secret_values(self) -> tuple[str, ...]:
        return configured_secret_values(self.repo_root)

    def _assert_no_configured_secrets(self, request_material: dict[str, Any]) -> None:
        for secret in self._configured_secret_values():
            assert_prompt_safe(request_material, known_secret=secret)

    @staticmethod
    def estimate_tokens(job: AssistiveJob, schema: dict[str, Any]) -> TokenEstimate:
        payload = job.prompt + job.source_excerpt + json.dumps(schema, ensure_ascii=False, sort_keys=True)
        # Deliberately conservative lexical estimate for admission; actual cost is settled from API usage.
        input_tokens = math.ceil(len(payload.encode("utf-8")) / 3) + 512
        return TokenEstimate(input_tokens, 0, job.max_output_tokens)

    def _request_body(self, job: AssistiveJob, schema: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": job.model,
            "input": [
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Return only evidence-backed candidate facts. Never guess. "
                                "When evidence is missing or contradictory, use UNKNOWN, NOT_PRESENT, or CONFLICT. "
                                "Every SUPPORTED fact requires an exact evidence locator. "
                                + job.prompt
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"TASK_ID={job.task_name}\n"
                                f"SOURCE_URL={job.source_url}\n"
                                f"SOURCE_CAPTURE_SHA256={job.source_capture_sha256}\n"
                                "SOURCE_EXCERPT_BEGIN\n"
                                f"{job.source_excerpt}\n"
                                "SOURCE_EXCERPT_END"
                            ),
                        }
                    ],
                },
            ],
            "max_output_tokens": job.max_output_tokens,
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "assistive_candidate",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        if body["store"] is not False:
            raise ControllerError("Responses storage must remain disabled")
        if self.policy.model(job.model).get("reasoning_parameter", True):
            body["reasoning"] = {"effort": job.reasoning_effort}
        return body

    def prepare(self, job: AssistiveJob, mode: ProcessingMode) -> dict[str, Any]:
        schema = self._load_schema(job.schema_path)
        self._validate_job(job, schema)
        body = self._request_body(job, schema)
        assert_prompt_safe(body)
        tokens = self.estimate_tokens(job, schema)
        cost = self.policy.estimate_cost(job.model, mode, tokens)
        identity = {
            "policy_id": self.policy.payload["policy_id"],
            "task_name": job.task_name,
            "jira_unit": job.jira_unit,
            "source_url": job.source_url,
            "source_capture_sha256": job.source_capture_sha256,
            "source_excerpt_sha256": hashlib.sha256(job.source_excerpt.encode("utf-8")).hexdigest(),
            "prompt_version": job.prompt_version,
            "prompt_sha256": hashlib.sha256(job.prompt.encode("utf-8")).hexdigest(),
            "schema_version": job.schema_version,
            "schema_sha256": sha256_value(schema),
            "model": job.model,
            "reasoning_effort": job.reasoning_effort,
            "allocation": job.allocation,
            "destination": job.destination,
            "mode": mode.value,
            "max_output_tokens": job.max_output_tokens,
        }
        request_id = sha256_value(identity)
        request_artifact = self.store.put_json(
            "requests", {"request_id": request_id, "identity": identity, "body": body}
        )
        return {
            "request_id": request_id,
            "identity": identity,
            "body": body,
            "schema": schema,
            "estimate": cost,
            "request_artifact": request_artifact,
        }

    def _cache_path(self, request_id: str) -> Path:
        return self.store.directory("manifests") / "requests" / f"{request_id}.json"

    @staticmethod
    def _write_atomic_json(destination: Path, value: dict[str, Any]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical_json_bytes(value) + b"\n"
        fd, temporary = tempfile.mkstemp(prefix=".manifest-", dir=destination.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _write_index_manifest(self, request_id: str, value: dict[str, Any]) -> None:
        self._write_atomic_json(self._cache_path(request_id), value)

    def _schema_reference(self, schema_path: Path) -> str:
        try:
            return schema_path.resolve(strict=True).relative_to(self.repo_root).as_posix()
        except (OSError, ValueError) as exc:
            raise ControllerError("schema path must resolve inside the authoritative repository") from exc

    def _resolve_schema_reference(self, reference: str) -> Path:
        try:
            candidate = (self.repo_root / reference).resolve(strict=True)
            candidate.relative_to(self.repo_root)
        except (OSError, ValueError) as exc:
            raise ControllerError("batch schema reference escapes the authoritative repository") from exc
        return candidate

    def _cached_result(self, request_id: str) -> AssistiveResult | None:
        path = self._cache_path(request_id)
        if not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("request_id") != request_id or value.get("status") != "COMPLETE":
            return None
        return AssistiveResult(
            request_id=request_id,
            disposition=value["disposition"],
            candidate=value.get("candidate"),
            validation_errors=tuple(value.get("validation_errors", [])),
            response_sha256=value["response_sha256"],
            actual_cost_usd=value["actual_cost_usd"],
            cached=True,
        )

    @staticmethod
    def _retryable(exc: Exception) -> bool:
        status = getattr(exc, "status_code", None)
        return status in {408, 409, 429} or isinstance(status, int) and status >= 500 or exc.__class__.__name__ in {
            "APIConnectionError",
            "APITimeoutError",
        }

    def _create_response(self, client: Any, body: dict[str, Any]) -> Any:
        attempts = int(self.policy.payload["api"]["max_transient_attempts"])
        for attempt in range(attempts):
            try:
                return client.responses.create(**body)
            except Exception as exc:
                if attempt + 1 == attempts or not self._retryable(exc):
                    raise
                time.sleep(min(8.0, 1.5 * (2**attempt)))
        raise AssertionError("unreachable")

    def _actual_cost(self, job: AssistiveJob, mode: ProcessingMode, usage: dict[str, int]) -> Decimal:
        estimate = self.policy.estimate_cost(
            job.model,
            mode,
            TokenEstimate(
                usage["input_tokens"],
                usage["cached_input_tokens"],
                usage["output_tokens"],
            ),
        )
        return estimate.amount_usd

    def _validate_candidate(
        self,
        response: dict[str, Any],
        schema: dict[str, Any],
        job: AssistiveJob,
    ) -> tuple[dict[str, Any] | None, list[str]]:
        try:
            text = _output_text(response)
            candidate = json.loads(text)
        except (ControllerError, json.JSONDecodeError) as exc:
            return None, [str(exc)]
        errors = validate_instance(candidate, schema)
        errors.extend(evidence_errors(candidate, capture_sha256=job.source_capture_sha256))
        allowed_dispositions = set(self.policy.payload["authority"]["allowed_destinations"])
        if candidate.get("disposition") not in allowed_dispositions:
            errors.append("candidate disposition is outside the candidate-only authority boundary")
        return candidate, errors

    def run_sync(self, job: AssistiveJob) -> AssistiveResult:
        prepared = self.prepare(job, ProcessingMode.SYNCHRONOUS)
        request_id = prepared["request_id"]
        cached = self._cached_result(request_id)
        if cached is not None:
            return cached
        estimate = prepared["estimate"]
        reservation = self.ledger.reserve(
            request_id=request_id,
            allocation=job.allocation,
            model=job.model,
            estimated_max_usd=estimate.amount_usd,
            priority=job.priority.value,
            jira_unit=job.jira_unit,
            release_reason=job.release_reason,
            admission_review_id=job.admission_review_id,
        )
        response_received = False
        try:
            self._assert_no_configured_secrets(prepared["body"])
            response_object = self._create_response(self._client(), prepared["body"])
            response_received = True
            response = _object_dict(response_object)
            response_artifact = self.store.put_json("responses", response)
            usage = _usage_dict(response)
            actual_cost = self._actual_cost(job, ProcessingMode.SYNCHRONOUS, usage)
            self.ledger.settle(reservation, actual_usd=actual_cost, usage=usage)
            candidate, errors = self._validate_candidate(response, prepared["schema"], job)
            disposition = candidate.get("disposition", job.destination) if candidate and not errors else "QUARANTINE"
            manifest = {
                "schema_version": 1,
                "status": "COMPLETE",
                "completed_at": _utc_now(),
                "request_id": request_id,
                "request_sha256": prepared["request_artifact"].sha256,
                "response_sha256": response_artifact.sha256,
                "source_capture_sha256": job.source_capture_sha256,
                "source_excerpt_sha256": prepared["identity"]["source_excerpt_sha256"],
                "prompt_sha256": prepared["identity"]["prompt_sha256"],
                "schema_sha256": prepared["identity"]["schema_sha256"],
                "model_requested": job.model,
                "model_returned": response.get("model", ""),
                "reasoning_effort": job.reasoning_effort,
                "jira_unit": job.jira_unit,
                "usage": usage,
                "estimated_max_usd": money(estimate.amount_usd),
                "actual_cost_usd": money(actual_cost),
                "validation_errors": errors,
                "disposition": disposition,
                "candidate": candidate,
                "authority": "CANDIDATE_ONLY",
            }
            manifest_artifact = self.store.put_json("manifests", manifest)
            manifest["manifest_sha256"] = manifest_artifact.sha256
            self._write_index_manifest(request_id, manifest)
            return AssistiveResult(
                request_id,
                disposition,
                candidate,
                tuple(errors),
                response_artifact.sha256,
                money(actual_cost),
                False,
            )
        except Exception:
            if not response_received:
                self.ledger.release(reservation, reason="NO_RESPONSE_RECEIVED")
            raise

    def prepare_batch_jsonl(self, jobs: list[AssistiveJob]) -> tuple[bytes, list[dict[str, Any]]]:
        if not jobs:
            raise ControllerError("batch must contain at least one job")
        prepared: list[dict[str, Any]] = []
        lines: list[bytes] = []
        seen: set[str] = set()
        for job in jobs:
            item = self.prepare(job, ProcessingMode.BATCH)
            if item["request_id"] in seen:
                raise ControllerError("batch contains a duplicate idempotent request")
            seen.add(item["request_id"])
            lines.append(
                canonical_json_bytes(
                    {
                        "custom_id": item["request_id"],
                        "method": "POST",
                        "url": "/v1/responses",
                        "body": item["body"],
                    }
                )
            )
            prepared.append({"job": job, **item})
        return b"\n".join(lines) + b"\n", prepared

    def submit_batch(self, jobs: list[AssistiveJob]) -> dict[str, Any]:
        payload, prepared = self.prepare_batch_jsonl(jobs)
        reservations: list[Reservation] = []
        client: Any | None = None
        input_file_id: str | None = None
        try:
            for item in prepared:
                self._assert_no_configured_secrets(item["body"])
            for item in prepared:
                job = item["job"]
                reservations.append(
                    self.ledger.reserve(
                        request_id=item["request_id"],
                        allocation=job.allocation,
                        model=job.model,
                        estimated_max_usd=item["estimate"].amount_usd,
                        priority=job.priority.value,
                        jira_unit=job.jira_unit,
                        release_reason=job.release_reason,
                        admission_review_id=job.admission_review_id,
                    )
                )
            artifact = self.store.put_bytes("batches", payload, suffix=".jsonl")
            client = self._client()
            with artifact.path.open("rb") as handle:
                remote_file = client.files.create(
                    file=handle,
                    purpose="batch",
                    expires_after={
                        "anchor": "created_at",
                        "seconds": int(self.policy.payload["api"]["remote_file_expiration_seconds"]),
                    },
                )
            remote_file_dict = _object_dict(remote_file)
            input_file_id = remote_file_dict["id"]
            batch = client.batches.create(
                input_file_id=input_file_id,
                endpoint="/v1/responses",
                completion_window=self.policy.payload["api"]["batch_completion_window"],
                metadata={"policy_id": self.policy.payload["policy_id"], "payload_sha256": artifact.sha256},
                output_expires_after={
                    "anchor": "created_at",
                    "seconds": int(self.policy.payload["api"]["remote_file_expiration_seconds"]),
                },
            )
            batch_dict = _object_dict(batch)
            manifest = {
                "schema_version": 1,
                "status": "SUBMITTED",
                "submitted_at": _utc_now(),
                "batch_id": batch_dict["id"],
                "input_file_id": input_file_id,
                "payload_sha256": artifact.sha256,
                "jobs": [
                    {
                        "request_id": item["request_id"],
                        "reservation_id": reservation.reservation_id,
                        "allocation": reservation.allocation,
                        "estimated_max_usd": money(reservation.estimated_max_usd),
                        "job": {
                            **asdict(item["job"]),
                            "schema_path": self._schema_reference(item["job"].schema_path),
                            "priority": item["job"].priority.value,
                        },
                    }
                    for item, reservation in zip(prepared, reservations)
                ],
            }
            self.store.put_json("manifests", manifest)
            path = self.store.directory("batches") / "active" / f"{batch_dict['id']}.json"
            self._write_atomic_json(path, manifest)
            return manifest
        except Exception:
            if client is not None and input_file_id is not None:
                try:
                    client.files.delete(input_file_id)
                except Exception:
                    pass
            for reservation in reservations:
                self.ledger.release(reservation, reason="BATCH_SUBMISSION_FAILED")
            raise

    def collect_batch(self, batch_id: str, *, delete_remote: bool = True) -> dict[str, Any]:
        path = self.store.directory("batches") / "active" / f"{batch_id}.json"
        if not path.is_file():
            raise ControllerError("unknown local batch identity")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        client = self._client()
        batch = _object_dict(client.batches.retrieve(batch_id))
        if batch.get("status") not in {"completed", "failed", "expired", "cancelled"}:
            return {"batch_id": batch_id, "status": batch.get("status", "unknown"), "terminal": False}
        output_id = batch.get("output_file_id")
        error_id = batch.get("error_file_id")
        output_payload = b""
        error_payload = b""
        if output_id:
            content = client.files.content(output_id)
            raw_content = getattr(content, "content", None)
            output_payload = bytes(raw_content if raw_content is not None else content.read())
            self.store.put_bytes("batches", output_payload, suffix=".output.jsonl")
        if error_id:
            content = client.files.content(error_id)
            raw_content = getattr(content, "content", None)
            error_payload = bytes(raw_content if raw_content is not None else content.read())
            self.store.put_bytes("batches", error_payload, suffix=".error.jsonl")
        results_by_id: dict[str, dict[str, Any]] = {}
        for raw in output_payload.splitlines():
            if raw.strip():
                item = json.loads(raw)
                results_by_id[item["custom_id"]] = item
        completed = quarantined = failed = 0
        for item in manifest["jobs"]:
            job_data = dict(item["job"])
            job_data["schema_path"] = self._resolve_schema_reference(job_data["schema_path"])
            job_data["priority"] = Priority(job_data["priority"])
            job = AssistiveJob(**job_data)
            reservation = Reservation(
                item["reservation_id"], item["request_id"], item["allocation"], job.model,
                Decimal(item["estimated_max_usd"])
            )
            line = results_by_id.get(item["request_id"])
            if not line or line.get("error"):
                self.ledger.release(reservation, reason="BATCH_ITEM_NO_SUCCESS_RESPONSE")
                failed += 1
                continue
            response = line.get("response", {})
            if int(response.get("status_code", 0)) != 200:
                self.ledger.release(reservation, reason="BATCH_ITEM_HTTP_FAILURE")
                failed += 1
                continue
            response_body = response.get("body", {})
            response_artifact = self.store.put_json("responses", response_body)
            usage = _usage_dict(response_body)
            actual = self._actual_cost(job, ProcessingMode.BATCH, usage)
            self.ledger.settle(reservation, actual_usd=actual, usage=usage)
            schema = self._load_schema(job.schema_path)
            candidate, errors = self._validate_candidate(response_body, schema, job)
            disposition = candidate.get("disposition", job.destination) if candidate and not errors else "QUARANTINE"
            quarantined += int(bool(errors))
            completed += 1
            request_manifest = {
                "schema_version": 1,
                "status": "COMPLETE",
                "completed_at": _utc_now(),
                "request_id": item["request_id"],
                "response_sha256": response_artifact.sha256,
                "actual_cost_usd": money(actual),
                "usage": usage,
                "candidate": candidate,
                "validation_errors": errors,
                "disposition": disposition,
                "authority": "CANDIDATE_ONLY",
            }
            self.store.put_json("manifests", request_manifest)
            self._write_index_manifest(item["request_id"], request_manifest)
        deleted: list[str] = []
        if delete_remote:
            for file_id in [manifest.get("input_file_id"), output_id, error_id]:
                if file_id:
                    try:
                        client.files.delete(file_id)
                        deleted.append(file_id)
                    except Exception:
                        pass
        final = {
            **manifest,
            "status": "COLLECTED",
            "provider_status": batch.get("status"),
            "collected_at": _utc_now(),
            "completed_items": completed,
            "quarantined_items": quarantined,
            "failed_items": failed,
            "remote_files_deleted": deleted,
            "error_payload_bytes": len(error_payload),
        }
        self._write_atomic_json(path, final)
        self.store.put_json("manifests", final)
        return final

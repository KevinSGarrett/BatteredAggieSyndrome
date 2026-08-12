from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict
from decimal import Decimal, ROUND_UP
from pathlib import Path

from .backend import AssistiveBackend, PermanentBackendError, TransientBackendError
from .budget import BudgetLedger, BudgetRejected
from .contracts import AssistiveRequest, DispatchResult, Disposition, sha256_value
from .redaction import contains_secret, redact
from .schemas import validate_output, validate_strict_schema
from .storage import ContentAddressedStore


class AssistiveDispatcher:
    def __init__(self, root: Path, backend: AssistiveBackend, policy_path: Path) -> None:
        self.root = root
        self.backend = backend
        self.policy = json.loads(policy_path.read_text(encoding="utf-8"))
        self.task_registry = json.loads(
            (root / "configs" / "openrouter_task_registry.json").read_text(encoding="utf-8")
        )
        self.store = ContentAddressedStore(Path(self.policy["storage"]["root"]))
        self.store.initialize()
        hard_limit = Decimal(str(self.policy["budget"]["paid_hard_limit_usd"]))
        self.ledger = BudgetLedger(self.store.root / "usage" / "ledger.json", hard_limit)

    def _cache_pointer(self, request_id: str) -> Path:
        return self.store.root / "runtime" / "request_cache" / f"{request_id}.json"

    def _write_cache_pointer(self, request_id: str, manifest_path: str) -> None:
        destination = self._cache_pointer(request_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"request_id": request_id, "manifest_path": manifest_path}, sort_keys=True).encode("utf-8") + b"\n"
        fd, temporary = tempfile.mkstemp(prefix=".cache-", dir=destination.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def estimate_cost(self, request: AssistiveRequest) -> Decimal:
        if request.model != self.policy["catalog"]["candidate_model"]:
            raise BudgetRejected("OPENROUTER_MODEL_PRICE_NOT_PINNED")
        pricing = self.policy["catalog"].get("observed_catalog_pricing_usd_per_token", {})
        if "input" not in pricing or "output" not in pricing:
            raise BudgetRejected("OPENROUTER_MODEL_PRICE_NOT_PINNED")
        input_characters = sum(len(item) for item in request.evidence_excerpts)
        estimated_input_tokens = max(1, (input_characters + 3) // 4)
        estimate = (
            Decimal(estimated_input_tokens) * Decimal(str(pricing["input"]))
            + Decimal(request.max_output_tokens) * Decimal(str(pricing["output"]))
        )
        return estimate.quantize(Decimal("0.000001"), rounding=ROUND_UP)

    def dispatch(self, request: AssistiveRequest, schema: dict[str, object]) -> DispatchResult:
        request_id = request.identity()
        validate_strict_schema(schema)
        task = self.task_registry.get("tasks", {}).get(request.task_id)
        if task is None:
            return self._record(request, Disposition.REJECTED, "UNREGISTERED_OPENROUTER_TASK", None)
        if task.get("authority") != request.authority.value:
            return self._record(request, Disposition.REJECTED, "TASK_AUTHORITY_MISMATCH", None)
        if task.get("jira_unit") != request.jira_unit:
            return self._record(request, Disposition.REJECTED, "TASK_JIRA_IDENTITY_MISMATCH", None)
        registered_schema = json.loads((self.root / task["schema"]).read_text(encoding="utf-8"))
        schema_hash = sha256_value(schema)
        if schema_hash != sha256_value(registered_schema) or request.schema_sha256 != schema_hash:
            return self._record(request, Disposition.REJECTED, "SCHEMA_IDENTITY_MISMATCH", None)
        if request.reasoning_effort not in self.policy["catalog"].get("candidate_allowed_reasoning_efforts", []):
            return self._record(request, Disposition.REJECTED, "REASONING_EFFORT_NOT_ALLOWED", None)
        cache = self._cache_pointer(request_id)
        if cache.is_file():
            pointer = json.loads(cache.read_text(encoding="utf-8"))
            return DispatchResult(request_id, Disposition.CANDIDATE, "CACHE_HIT", pointer["manifest_path"], None)
        if any(contains_secret(excerpt) for excerpt in request.evidence_excerpts):
            return self._record(request, Disposition.REJECTED, "SECRET_DETECTED", None)
        sanitized = asdict(request)
        sanitized["authority"] = request.authority.value
        sanitized["evidence_excerpts"] = [redact(item) for item in request.evidence_excerpts]
        self.store.put_json("requests", sanitized)
        try:
            estimate_usd = self.estimate_cost(request)
            self.ledger.reserve(request_id, estimate_usd)
        except BudgetRejected as exc:
            return self._record(request, Disposition.REJECTED, str(exc), None)
        result = None
        attempts = int(self.policy["api"].get("max_transient_attempts", 3))
        try:
            for attempt in range(1, attempts + 1):
                try:
                    result = self.backend.submit(request, schema)
                    break
                except TransientBackendError:
                    if attempt == attempts:
                        raise
                    time.sleep(min(0.05 * (2 ** (attempt - 1)), 0.2))
                except PermanentBackendError:
                    raise
        except (TransientBackendError, PermanentBackendError) as exc:
            self.ledger.release(request_id)
            return self._record(request, Disposition.REJECTED, f"PROVIDER_FAILURE:{type(exc).__name__}", None)
        if result is None:
            self.ledger.release(request_id)
            return self._record(request, Disposition.REJECTED, "PROVIDER_RESULT_ABSENT", None)
        if result.cost_usd is None:
            self.store.put_json(
                "quarantine",
                {**asdict(result), "request_id": request_id, "reason": "PROVIDER_COST_MISSING"},
            )
            self.ledger.release(request_id)
            return self._record(request, Disposition.QUARANTINE, "PROVIDER_COST_MISSING", result)
        if result.model_resolved != request.model:
            self.store.put_json(
                "quarantine",
                {**asdict(result), "request_id": request_id, "reason": "UNEXPECTED_MODEL_RESOLUTION"},
            )
            self.ledger.release(request_id)
            return self._record(request, Disposition.QUARANTINE, "UNEXPECTED_MODEL_RESOLUTION", result)
        try:
            validate_output(result.output, schema)
        except ValueError as exc:
            self.store.put_json(
                "quarantine",
                {**asdict(result), "request_id": request_id, "reason": f"STRICT_OUTPUT_INVALID:{exc}"},
            )
            self.ledger.release(request_id)
            return self._record(request, Disposition.QUARANTINE, f"STRICT_OUTPUT_INVALID:{exc}", result)
        self.store.put_json("responses", {**asdict(result), "request_id": request_id})
        try:
            self.ledger.settle(request_id, Decimal(result.cost_usd))
        except BudgetRejected as exc:
            self.ledger.release(request_id)
            return self._record(request, Disposition.QUARANTINE, str(exc), result)
        final = self._record(request, Disposition.CANDIDATE, "CANDIDATE_ONLY_VALIDATED", result)
        self._write_cache_pointer(request_id, final.manifest_path)
        return final

    def _record(self, request: AssistiveRequest, disposition: Disposition, reason: str, result: object) -> DispatchResult:
        request_id = request.identity()
        manifest = {
            "schema_version": 1,
            "request_id": request_id,
            "task_id": request.task_id,
            "jira_unit": request.jira_unit,
            "authority": request.authority.value,
            "provider": self.backend.name,
            "disposition": disposition.value,
            "reason": reason,
            "paid_hard_limit_usd": str(self.ledger.hard_limit_usd),
            "canonical_write_authority": False,
            "protected_decision_authority": False,
        }
        path, _, _ = self.store.put_json("manifests", manifest)
        return DispatchResult(request_id, disposition, reason, str(path), result if hasattr(result, "output") else None)

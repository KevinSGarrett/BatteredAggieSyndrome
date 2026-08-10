from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

from .contracts import money
from .policy import AssistivePolicy


class BudgetError(RuntimeError):
    pass


@dataclass(frozen=True)
class Reservation:
    reservation_id: str
    request_id: str
    allocation: str
    model: str
    estimated_max_usd: Decimal


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class UsageLedger:
    def __init__(self, policy: AssistivePolicy, usage_root: Path) -> None:
        self.policy = policy
        self.path = usage_root / "usage-ledger.jsonl"
        self.lock_path = usage_root / ".usage-ledger.lock"
        usage_root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _lock(self, timeout_seconds: float = 10.0) -> Iterator[None]:
        deadline = time.monotonic() + timeout_seconds
        fd: int | None = None
        while fd is None:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"pid={os.getpid()}\n".encode("ascii"))
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise BudgetError("usage ledger is locked by another process")
                time.sleep(0.05)
        try:
            yield
        finally:
            os.close(fd)
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events = []
        for line_number, raw in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise BudgetError(f"usage ledger line {line_number} is corrupt") from exc
            events.append(event)
        return events

    def _canonical_allocation(self, allocation: str) -> str:
        aliases = self.policy.payload["budget"].get("legacy_allocation_map", {})
        return aliases.get(allocation, allocation)

    def _summary(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        outstanding: dict[str, Decimal] = {}
        allocations: dict[str, Decimal] = {}
        models: dict[str, Decimal] = {}
        settled = Decimal("0")
        stage_limit = Decimal(self.policy.payload["budget"]["initial_stage_limit_usd"])
        for event in events:
            kind = event.get("event")
            rid = event.get("reservation_id", "")
            if kind == "RESERVED":
                amount = Decimal(event["estimated_max_usd"])
                outstanding[rid] = amount
            elif kind in {"SETTLED", "RELEASED"}:
                outstanding.pop(rid, None)
                if kind == "SETTLED":
                    actual = Decimal(event["actual_usd"])
                    settled += actual
                    allocation = self._canonical_allocation(event["allocation"])
                    allocations[allocation] = allocations.get(allocation, Decimal("0")) + actual
                    model = event.get("model")
                    if model:
                        models[model] = models.get(model, Decimal("0")) + actual
            elif kind == "BUDGET_STAGE_RELEASED":
                stage_limit = max(stage_limit, Decimal(event["stage_limit_usd"]))
        return {
            "settled_usd": settled,
            "reserved_usd": sum(outstanding.values(), Decimal("0")),
            "allocations": allocations,
            "models": models,
            "outstanding": outstanding,
            "stage_limit_usd": stage_limit,
        }

    def summary(self) -> dict[str, Any]:
        value = self._summary(self.events())
        reported_models = dict(value["models"])
        for model, amount in self.policy.payload["budget"].get("historical_model_spend_usd", {}).items():
            reported_models[model] = reported_models.get(model, Decimal("0")) + Decimal(amount)
        return {
            "settled_usd": money(value["settled_usd"]),
            "reserved_usd": money(value["reserved_usd"]),
            "committed_usd": money(value["settled_usd"] + value["reserved_usd"]),
            "remaining_usd": money(self.policy.budget_limit - value["settled_usd"] - value["reserved_usd"]),
            "stage_limit_usd": money(value["stage_limit_usd"]),
            "allocations": {key: money(amount) for key, amount in sorted(value["allocations"].items())},
            "models": {key: money(amount) for key, amount in sorted(reported_models.items())},
        }

    def _append(self, event: dict[str, Any]) -> None:
        event = {"schema_version": 1, "recorded_at": _utc_now(), **event}
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        with self.path.open("a", encoding="utf-8", newline="") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    def reserve(
        self,
        *,
        request_id: str,
        allocation: str,
        model: str,
        estimated_max_usd: Decimal,
        priority: str,
        jira_unit: str,
        release_reason: str | None = None,
        admission_review_id: str | None = None,
    ) -> Reservation:
        if estimated_max_usd <= 0:
            raise BudgetError("reservation must be positive")
        budget = self.policy.payload["budget"]
        if allocation not in budget["allocations"]:
            raise BudgetError(f"unknown budget allocation: {allocation}")
        with self._lock():
            events = self.events()
            state = self._summary(events)
            for event in events:
                if event.get("event") == "RESERVED" and event.get("request_id") == request_id:
                    if event.get("reservation_id") in state["outstanding"]:
                        return Reservation(
                            event["reservation_id"], request_id, allocation, model,
                            Decimal(event["estimated_max_usd"])
                        )
            committed = state["settled_usd"] + state["reserved_usd"]
            if committed >= Decimal(budget["low_priority_stop_usd"]) and priority == "LOW":
                raise BudgetError("low-priority admission stops at USD 90")
            allocation_used = state["allocations"].get(allocation, Decimal("0"))
            allocation_reserved = sum(
                Decimal(event["estimated_max_usd"])
                for event in events
                if event.get("event") == "RESERVED"
                and event.get("allocation") == allocation
                and event.get("reservation_id") in state["outstanding"]
            )
            allocation_cap = Decimal(budget["allocations"][allocation])
            if allocation_used + allocation_reserved + estimated_max_usd > allocation_cap:
                raise BudgetError(f"allocation cap exceeded: {allocation}")
            if estimated_max_usd > Decimal(budget["single_job_review_usd"]) and not admission_review_id:
                raise BudgetError("job above USD 1 requires a recorded admission review")
            if committed + estimated_max_usd > state["stage_limit_usd"]:
                raise BudgetError("current staged budget release would be exceeded")
            if allocation == "VALUE_GATED_RESERVE":
                allowed_reasons = set(budget["reserve_release_requires"])
                completion_reason = budget.get("completion_release_reason", "COMPLETION_OR_CONTINGENCY")
                if release_reason not in allowed_reasons | {completion_reason}:
                    raise BudgetError("value-gated reserve lacks measured value or completion evidence")
                reserve_used = state["allocations"].get(allocation, Decimal("0"))
                if state["stage_limit_usd"] < self.policy.budget_limit:
                    usable = allocation_cap - Decimal(budget["completion_contingency_minimum_usd"])
                    if reserve_used + allocation_reserved + estimated_max_usd > usable:
                        raise BudgetError("USD 5 completion/contingency reserve must remain locked")
                elif reserve_used + allocation_reserved >= allocation_cap - Decimal(
                    budget["completion_contingency_minimum_usd"]
                ) and release_reason != completion_reason:
                    raise BudgetError("final reserve requires completion/contingency admission")
            model_caps = budget.get("model_caps", {})
            if model in model_caps:
                historical = Decimal(budget.get("historical_model_spend_usd", {}).get(model, "0"))
                model_used = historical + state["models"].get(model, Decimal("0"))
                model_reserved = sum(
                    Decimal(event["estimated_max_usd"])
                    for event in events
                    if event.get("event") == "RESERVED"
                    and event.get("model") == model
                    and event.get("reservation_id") in state["outstanding"]
                )
                cap_spec = model_caps[model]
                model_cap = Decimal(cap_spec["base_usd"])
                if allocation == "VALUE_GATED_RESERVE" and release_reason in set(budget["reserve_release_requires"]):
                    model_cap = Decimal(cap_spec["reserve_max_usd"])
                if model_used + model_reserved + estimated_max_usd > model_cap:
                    raise BudgetError(f"model cap exceeded: {model}")
            if committed + estimated_max_usd > self.policy.budget_limit:
                raise BudgetError("absolute USD 100 budget hard stop")
            reservation = Reservation(str(uuid.uuid4()), request_id, allocation, model, estimated_max_usd)
            self._append(
                {
                    "event": "RESERVED",
                    "reservation_id": reservation.reservation_id,
                    "request_id": request_id,
                    "allocation": allocation,
                    "model": model,
                    "estimated_max_usd": money(estimated_max_usd),
                    "priority": priority,
                    "jira_unit": jira_unit,
                    "release_reason": release_reason,
                    "admission_review_id": admission_review_id,
                }
            )
            return reservation

    def settle(self, reservation: Reservation, *, actual_usd: Decimal, usage: dict[str, int]) -> None:
        if actual_usd < 0 or actual_usd > reservation.estimated_max_usd:
            raise BudgetError("actual cost is outside the reserved maximum")
        with self._lock():
            events = self.events()
            state = self._summary(events)
            if reservation.reservation_id not in state["outstanding"]:
                raise BudgetError("reservation is not outstanding")
            self._append(
                {
                    "event": "SETTLED",
                    "reservation_id": reservation.reservation_id,
                    "request_id": reservation.request_id,
                    "allocation": reservation.allocation,
                    "model": reservation.model,
                    "estimated_max_usd": money(reservation.estimated_max_usd),
                    "actual_usd": money(actual_usd),
                    "usage": usage,
                }
            )
            new_settled = state["settled_usd"] + actual_usd
            already_alerted = {
                event.get("threshold_usd")
                for event in events
                if event.get("event") == "ALERT_THRESHOLD_REACHED"
            }
            for threshold_raw in self.policy.payload["budget"]["alert_thresholds_usd"]:
                threshold = Decimal(threshold_raw)
                if state["settled_usd"] < threshold <= new_settled and threshold_raw not in already_alerted:
                    self._append(
                        {
                            "event": "ALERT_THRESHOLD_REACHED",
                            "threshold_usd": threshold_raw,
                            "settled_usd": money(new_settled),
                        }
                    )

    def release(self, reservation: Reservation, *, reason: str) -> None:
        with self._lock():
            state = self._summary(self.events())
            if reservation.reservation_id not in state["outstanding"]:
                return
            self._append(
                {
                    "event": "RELEASED",
                    "reservation_id": reservation.reservation_id,
                    "request_id": reservation.request_id,
                    "allocation": reservation.allocation,
                    "model": reservation.model,
                    "reason": reason,
                }
            )

    def release_stage(self, stage_limit_usd: Decimal, *, evidence_id: str, reason: str) -> None:
        budget = self.policy.payload["budget"]
        allowed = {Decimal(value) for value in budget["stage_limits_usd"]}
        if stage_limit_usd not in allowed or stage_limit_usd <= Decimal(budget["initial_stage_limit_usd"]):
            raise BudgetError("invalid staged budget release")
        expected = budget["stage_release_requires"].get(f"{stage_limit_usd:.2f}")
        if reason != expected or not evidence_id.strip():
            raise BudgetError("staged budget release lacks the required evidence reason")
        with self._lock():
            state = self._summary(self.events())
            if stage_limit_usd <= state["stage_limit_usd"]:
                return
            prior_limits = sorted(value for value in allowed if value < stage_limit_usd)
            if prior_limits and state["stage_limit_usd"] < prior_limits[-1]:
                raise BudgetError("budget stages must be released in order")
            self._append(
                {
                    "event": "BUDGET_STAGE_RELEASED",
                    "stage_limit_usd": money(stage_limit_usd),
                    "evidence_id": evidence_id,
                    "reason": reason,
                }
            )

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

    @staticmethod
    def _summary(events: list[dict[str, Any]]) -> dict[str, Any]:
        outstanding: dict[str, Decimal] = {}
        allocations: dict[str, Decimal] = {}
        settled = Decimal("0")
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
                    allocation = event["allocation"]
                    allocations[allocation] = allocations.get(allocation, Decimal("0")) + actual
        return {
            "settled_usd": settled,
            "reserved_usd": sum(outstanding.values(), Decimal("0")),
            "allocations": allocations,
            "outstanding": outstanding,
        }

    def summary(self) -> dict[str, Any]:
        value = self._summary(self.events())
        return {
            "settled_usd": money(value["settled_usd"]),
            "reserved_usd": money(value["reserved_usd"]),
            "committed_usd": money(value["settled_usd"] + value["reserved_usd"]),
            "remaining_usd": money(self.policy.budget_limit - value["settled_usd"] - value["reserved_usd"]),
            "allocations": {key: money(amount) for key, amount in sorted(value["allocations"].items())},
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
        estimated_max_usd: Decimal,
        priority: str,
        jira_unit: str,
        release_reason: str | None = None,
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
                            event["reservation_id"], request_id, allocation, Decimal(event["estimated_max_usd"])
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
                if allocation != "CONTINGENCY_COMPLETION":
                    raise BudgetError(f"allocation cap exceeded: {allocation}")
                if release_reason not in set(budget["reserve_release_requires"]):
                    raise BudgetError("contingency release lacks an allowed high-value reason")
            if committed + estimated_max_usd > self.policy.budget_limit:
                raise BudgetError("absolute USD 100 budget hard stop")
            reservation = Reservation(str(uuid.uuid4()), request_id, allocation, estimated_max_usd)
            self._append(
                {
                    "event": "RESERVED",
                    "reservation_id": reservation.reservation_id,
                    "request_id": request_id,
                    "allocation": allocation,
                    "estimated_max_usd": money(estimated_max_usd),
                    "priority": priority,
                    "jira_unit": jira_unit,
                    "release_reason": release_reason,
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
                    "reason": reason,
                }
            )

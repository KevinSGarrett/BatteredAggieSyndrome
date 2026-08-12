from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


class BudgetRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class BudgetState:
    hard_limit_usd: Decimal
    settled_usd: Decimal
    reserved_usd: Decimal


class BudgetLedger:
    def __init__(self, path: Path, hard_limit_usd: Decimal) -> None:
        self.path = path
        self.hard_limit_usd = hard_limit_usd

    def _load(self) -> dict[str, object]:
        if not self.path.exists():
            return {"schema_version": 1, "settled_usd": "0.000000", "reservations": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def state(self) -> BudgetState:
        data = self._load()
        reservations = data.get("reservations", {})
        return BudgetState(
            self.hard_limit_usd,
            Decimal(str(data.get("settled_usd", "0"))),
            sum((Decimal(str(v)) for v in reservations.values()), Decimal("0")),
        )

    def reserve(self, request_id: str, estimate_usd: Decimal) -> None:
        if estimate_usd <= 0:
            raise BudgetRejected("PAID_OPENROUTER_COST_ESTIMATE_REQUIRED")
        data = self._load()
        reservations = dict(data.get("reservations", {}))
        if request_id in reservations:
            return
        state = self.state()
        if state.settled_usd + state.reserved_usd + estimate_usd > self.hard_limit_usd:
            raise BudgetRejected("PAID_OPENROUTER_BUDGET_NOT_AUTHORIZED")
        reservations[request_id] = format(estimate_usd, "f")
        data["reservations"] = reservations
        self._write(data)

    def settle(self, request_id: str, actual_usd: Decimal) -> None:
        if actual_usd < 0:
            raise BudgetRejected("OPENROUTER_NEGATIVE_COST_INVALID")
        data = self._load()
        reservations = dict(data.get("reservations", {}))
        if request_id not in reservations:
            raise BudgetRejected("OPENROUTER_RESERVATION_NOT_FOUND")
        settled = Decimal(str(data.get("settled_usd", "0")))
        other_reserved = sum(
            (Decimal(str(value)) for key, value in reservations.items() if key != request_id),
            Decimal("0"),
        )
        if settled + other_reserved + actual_usd > self.hard_limit_usd:
            raise BudgetRejected("OPENROUTER_ACTUAL_COST_EXCEEDS_HARD_LIMIT")
        reservations.pop(request_id)
        data["reservations"] = reservations
        data["settled_usd"] = format(settled + actual_usd, "f")
        self._write(data)

    def release(self, request_id: str) -> None:
        data = self._load()
        reservations = dict(data.get("reservations", {}))
        if request_id in reservations:
            reservations.pop(request_id)
            data["reservations"] = reservations
            self._write(data)

    def _write(self, data: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".ledger-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

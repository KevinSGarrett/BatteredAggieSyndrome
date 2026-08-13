from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


class BudgetRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class BudgetState:
    hard_limit_usd: Decimal
    released_limit_usd: Decimal
    settled_usd: Decimal
    reserved_usd: Decimal


class BudgetLedger:
    def __init__(self, path: Path, hard_limit_usd: Decimal, released_limit_usd: Decimal | None = None) -> None:
        self.path = path
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self.hard_limit_usd = hard_limit_usd
        self.released_limit_usd = released_limit_usd if released_limit_usd is not None else hard_limit_usd
        if self.released_limit_usd < 0 or self.released_limit_usd > self.hard_limit_usd:
            raise BudgetRejected("PROVIDER_RELEASED_STAGE_INVALID")

    @contextmanager
    def _lock(self, timeout_seconds: float = 10.0):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        initialization_deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                descriptor = os.open(
                    self.lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
            except FileExistsError:
                if self.lock_path.stat().st_size >= 1:
                    break
                if time.monotonic() >= initialization_deadline:
                    raise BudgetRejected("PROVIDER_BUDGET_LEDGER_LOCK_INITIALIZATION_TIMEOUT")
                time.sleep(0.02)
            else:
                try:
                    os.write(descriptor, b"0")
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                break
        handle = self.lock_path.open("r+b")
        handle.seek(0)
        deadline = time.monotonic() + timeout_seconds
        acquired = False
        try:
            while not acquired:
                try:
                    handle.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except (OSError, BlockingIOError):
                    if time.monotonic() >= deadline:
                        raise BudgetRejected("PROVIDER_BUDGET_LEDGER_LOCK_TIMEOUT")
                    time.sleep(0.02)
            yield
        finally:
            if acquired:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def _load(self) -> dict[str, object]:
        if not self.path.exists():
            return {"schema_version": 1, "settled_usd": "0.000000", "reservations": {}, "settlements": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def state(self) -> BudgetState:
        data = self._load()
        reservations = data.get("reservations", {})
        return BudgetState(
            self.hard_limit_usd,
            self.released_limit_usd,
            Decimal(str(data.get("settled_usd", "0"))),
            sum((Decimal(str(v)) for v in reservations.values()), Decimal("0")),
        )

    def settled_amount(self, request_id: str) -> Decimal | None:
        """Return an exact prior settlement for restart-safe provider recovery."""
        with self._lock():
            settlements = dict(self._load().get("settlements", {}))
            if request_id not in settlements:
                return None
            return Decimal(str(settlements[request_id]))

    def reserve(self, request_id: str, estimate_usd: Decimal) -> None:
        if estimate_usd <= 0:
            raise BudgetRejected("PAID_OPENROUTER_COST_ESTIMATE_REQUIRED")
        with self._lock():
            data = self._load()
            reservations = dict(data.get("reservations", {}))
            settlements = dict(data.get("settlements", {}))
            if request_id in settlements:
                raise BudgetRejected("PROVIDER_REQUEST_ALREADY_SETTLED")
            if request_id in reservations:
                if Decimal(str(reservations[request_id])) != estimate_usd:
                    raise BudgetRejected("PROVIDER_RESERVATION_IDEMPOTENCY_CONFLICT")
                return
            state = self.state()
            if state.settled_usd + state.reserved_usd + estimate_usd > self.released_limit_usd:
                raise BudgetRejected("PROVIDER_RELEASED_STAGE_EXCEEDED")
            reservations[request_id] = format(estimate_usd, "f")
            data["reservations"] = reservations
            self._write(data)

    def settle(self, request_id: str, actual_usd: Decimal) -> None:
        if actual_usd < 0:
            raise BudgetRejected("OPENROUTER_NEGATIVE_COST_INVALID")
        with self._lock():
            data = self._load()
            reservations = dict(data.get("reservations", {}))
            settlements = dict(data.get("settlements", {}))
            if request_id in settlements:
                if Decimal(str(settlements[request_id])) != actual_usd:
                    raise BudgetRejected("PROVIDER_SETTLEMENT_IDEMPOTENCY_CONFLICT")
                return
            if request_id not in reservations:
                raise BudgetRejected("OPENROUTER_RESERVATION_NOT_FOUND")
            settled = Decimal(str(data.get("settled_usd", "0")))
            other_reserved = sum(
                (Decimal(str(value)) for key, value in reservations.items() if key != request_id),
                Decimal("0"),
            )
            if settled + other_reserved + actual_usd > self.released_limit_usd:
                raise BudgetRejected("PROVIDER_ACTUAL_COST_EXCEEDS_RELEASED_STAGE")
            reservations.pop(request_id)
            data["reservations"] = reservations
            settlements[request_id] = format(actual_usd, "f")
            data["settlements"] = settlements
            data["settled_usd"] = format(settled + actual_usd, "f")
            self._write(data)

    def release(self, request_id: str) -> None:
        with self._lock():
            data = self._load()
            reservations = dict(data.get("reservations", {}))
            if request_id in reservations:
                reservations.pop(request_id)
                data["reservations"] = reservations
                self._write(data)

    def reconcile_provider_total(self, actual_total_usd: Decimal, *, evidence_sha256: str) -> None:
        if actual_total_usd < 0:
            raise BudgetRejected("PROVIDER_TOTAL_COST_INVALID")
        with self._lock():
            data = self._load()
            settled = Decimal(str(data.get("settled_usd", "0")))
            if actual_total_usd > self.released_limit_usd:
                raise BudgetRejected("PROVIDER_TOTAL_EXCEEDS_RELEASED_STAGE")
            reconciled_total = max(actual_total_usd, settled)
            data["settled_usd"] = format(reconciled_total, "f")
            if actual_total_usd >= settled:
                data["reservations"] = {}
            data["provider_reconciliation"] = {
                "evidence_sha256": evidence_sha256,
                "provider_total_usd": format(actual_total_usd, "f"),
                "local_settled_before_usd": format(settled, "f"),
                "status": "PROVIDER_TOTAL_RECONCILED" if actual_total_usd >= settled else "PROVIDER_TOTAL_LAGGING_LOCAL_SETTLEMENT",
                "conservative_all_key_usage_counted": True,
            }
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

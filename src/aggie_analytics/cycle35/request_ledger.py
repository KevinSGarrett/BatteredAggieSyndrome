"""R35-05/11/12/13: one shared, honest request ledger.

Two ceilings govern this cycle: 50 free public coaching/history requests and
50 free availability/context requests. Several rules follow from the pack and
are enforced here rather than remembered:

* **Retries and pagination count.** A request that failed and was retried
  spent budget twice. A paginated endpoint spends one unit per page. A ledger
  that counts only "logical acquisitions" understates what was used.
* **Cache first.** A cached response satisfies a need without spending
  budget, and the ledger records it as a cache hit so the distinction between
  "we had it" and "we fetched it" survives.
* **An unattempted request is not "source unavailable".** NOT_ATTEMPTED and
  ATTEMPTED_AND_FAILED are different outcomes and never collapse.
* **Budget exhaustion is not verification.** Running out of requests leaves
  the remaining keys UNMET with a resumable queue, never "verified".

GitHub and Jira requests are recorded explicitly and separately, because they
are infrastructure readback rather than scientific acquisition and must not
silently consume a scientific budget.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

BUDGET_COACHING = "coaching_history"
BUDGET_AVAILABILITY = "availability_context"
BUDGET_INFRASTRUCTURE = "infrastructure_readback"

CEILINGS = {BUDGET_COACHING: 50, BUDGET_AVAILABILITY: 50}

OUTCOME_CACHE_HIT = "CACHE_HIT_NO_REQUEST_SPENT"
OUTCOME_OK = "FETCHED_OK"
OUTCOME_FAILED = "ATTEMPTED_AND_FAILED"
OUTCOME_REFUSED = "REFUSED_BY_BUDGET"
OUTCOME_NOT_ATTEMPTED = "NOT_ATTEMPTED"


class BudgetExhausted(RuntimeError):
    """Raised when a ceiling is reached. Never downgraded to 'unavailable'."""


@dataclass
class RequestLedger:
    """Every network attempt this cycle makes, with its exact cost."""

    entries: list[dict[str, Any]] = field(default_factory=list)
    spent: dict[str, int] = field(
        default_factory=lambda: {
            BUDGET_COACHING: 0,
            BUDGET_AVAILABILITY: 0,
            BUDGET_INFRASTRUCTURE: 0,
        }
    )

    def remaining(self, budget: str) -> int:
        ceiling = CEILINGS.get(budget)
        if ceiling is None:
            return 1_000_000  # infrastructure readback has no scientific ceiling
        return ceiling - self.spent.get(budget, 0)

    def record(
        self,
        *,
        budget: str,
        url: str,
        purpose: str,
        outcome: str,
        attempt: int = 1,
        page: int | None = None,
        status: int | None = None,
        bytes_received: int | None = None,
        detail: str = "",
    ) -> dict[str, Any]:
        spends = outcome in {OUTCOME_OK, OUTCOME_FAILED}
        if spends:
            self.spent[budget] = self.spent.get(budget, 0) + 1
        entry = {
            "at_utc": datetime.now(timezone.utc).isoformat(),
            "budget": budget,
            "url": url,
            "purpose": purpose,
            "outcome": outcome,
            "attempt": attempt,
            "page": page,
            "http_status": status,
            "bytes_received": bytes_received,
            "spent_a_request": spends,
            "detail": detail,
        }
        self.entries.append(entry)
        return entry

    def fetch(
        self,
        *,
        budget: str,
        url: str,
        purpose: str,
        fetcher: Callable[[], tuple[int, bytes]],
        cache_path: Path | None = None,
        max_attempts: int = 2,
        backoff_seconds: float = 2.0,
        page: int | None = None,
    ) -> dict[str, Any]:
        """Cache-first fetch with bounded, COUNTED retries."""

        if cache_path is not None and Path(cache_path).is_file():
            raw = Path(cache_path).read_bytes()
            self.record(
                budget=budget,
                url=url,
                purpose=purpose,
                outcome=OUTCOME_CACHE_HIT,
                page=page,
                bytes_received=len(raw),
                detail="served from " + str(cache_path),
            )
            return {"ok": True, "body": raw, "from_cache": True}

        last_detail = ""
        for attempt in range(1, max_attempts + 1):
            if self.remaining(budget) <= 0:
                self.record(
                    budget=budget,
                    url=url,
                    purpose=purpose,
                    outcome=OUTCOME_REFUSED,
                    attempt=attempt,
                    page=page,
                    detail="ceiling reached; not attempted",
                )
                raise BudgetExhausted(
                    budget + " ceiling reached before " + url
                )
            try:
                status, body = fetcher()
            except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
                last_detail = type(exc).__name__ + ": " + str(exc)
                self.record(
                    budget=budget,
                    url=url,
                    purpose=purpose,
                    outcome=OUTCOME_FAILED,
                    attempt=attempt,
                    page=page,
                    detail=last_detail,
                )
                if attempt < max_attempts:
                    time.sleep(backoff_seconds * attempt)
                continue
            if 200 <= status < 300:
                self.record(
                    budget=budget,
                    url=url,
                    purpose=purpose,
                    outcome=OUTCOME_OK,
                    attempt=attempt,
                    page=page,
                    status=status,
                    bytes_received=len(body),
                )
                if cache_path is not None:
                    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(cache_path).write_bytes(body)
                return {"ok": True, "body": body, "from_cache": False,
                        "status": status}
            last_detail = "HTTP " + str(status)
            self.record(
                budget=budget,
                url=url,
                purpose=purpose,
                outcome=OUTCOME_FAILED,
                attempt=attempt,
                page=page,
                status=status,
                detail=last_detail,
            )
            if attempt < max_attempts:
                time.sleep(backoff_seconds * attempt)
        return {"ok": False, "body": b"", "detail": last_detail}

    def as_dict(self) -> dict[str, Any]:
        outcomes: dict[str, int] = {}
        for entry in self.entries:
            outcomes[entry["outcome"]] = outcomes.get(entry["outcome"], 0) + 1
        return {
            "artifact_type": "CYCLE35_REQUEST_LEDGER",
            "ceilings": dict(CEILINGS),
            "spent": dict(self.spent),
            "remaining": {
                budget: self.remaining(budget) for budget in CEILINGS
            },
            "entry_count": len(self.entries),
            "outcome_counts": outcomes,
            "entries": self.entries,
            "retries_and_pagination_counted": True,
            "cache_hits_do_not_spend_budget": True,
            "unattempted_is_not_source_unavailable": True,
            "budget_exhaustion_is_not_verification": True,
        }

    def write(self, path: Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(self.as_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )

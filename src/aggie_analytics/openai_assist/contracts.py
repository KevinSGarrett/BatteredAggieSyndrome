from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_UP
from enum import StrEnum
from typing import Any


class Disposition(StrEnum):
    CANDIDATE = "CANDIDATE"
    REVIEW = "REVIEW"
    QUARANTINE = "QUARANTINE"
    REJECTED = "REJECTED"


class Priority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class ProcessingMode(StrEnum):
    SYNCHRONOUS = "SYNCHRONOUS"
    BATCH = "BATCH"


@dataclass(frozen=True)
class TokenEstimate:
    input_tokens: int
    cached_input_tokens: int
    max_output_tokens: int


@dataclass(frozen=True)
class CostEstimate:
    amount_usd: Decimal
    model: str
    mode: ProcessingMode
    tokens: TokenEstimate

    def json_value(self) -> dict[str, Any]:
        value = asdict(self)
        value["amount_usd"] = money(self.amount_usd)
        value["mode"] = self.mode.value
        return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def money(value: Decimal | str | int | float) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_UP))

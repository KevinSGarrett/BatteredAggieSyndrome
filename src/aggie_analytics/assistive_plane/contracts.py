from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class Authority(StrEnum):
    PATCH_CANDIDATE = "PATCH_CANDIDATE"
    INDEPENDENT_REVIEW = "INDEPENDENT_REVIEW"
    RECONCILIATION_RANKING = "RECONCILIATION_RANKING"
    SCHEMA_DRIFT_REVIEW = "SCHEMA_DRIFT_REVIEW"
    VISUAL_LAYOUT_TRIAGE = "VISUAL_LAYOUT_TRIAGE"


class Disposition(StrEnum):
    CANDIDATE = "CANDIDATE"
    REVIEW = "REVIEW"
    QUARANTINE = "QUARANTINE"
    REJECTED = "REJECTED"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True)
class AssistiveRequest:
    task_id: str
    jira_unit: str
    base_commit: str
    authority: Authority
    prompt_version: str
    schema_version: str
    schema_sha256: str
    source_hashes: tuple[str, ...]
    evidence_excerpts: tuple[str, ...]
    model: str
    reasoning_effort: str
    max_output_tokens: int
    provider_policy_version: str

    def identity(self) -> str:
        return sha256_value(asdict(self))


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    model_requested: str
    model_resolved: str
    output: dict[str, Any]
    usage: dict[str, Any]
    raw_response_id: str
    cost_usd: str | None


@dataclass(frozen=True)
class DispatchResult:
    request_id: str
    disposition: Disposition
    reason: str
    manifest_path: str
    provider_result: ProviderResult | None = None

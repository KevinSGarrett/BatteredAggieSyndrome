from __future__ import annotations
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class SourceRightsAction(str, Enum):
    ACQUIRE_PRODUCTION = "ACQUIRE_PRODUCTION"
    ACQUIRE_EXPERIMENTAL = "ACQUIRE_EXPERIMENTAL"
    EXPORT_RAW = "EXPORT_RAW"
    EXPORT_DERIVED = "EXPORT_DERIVED"
    TRAIN_LOCAL = "TRAIN_LOCAL"


class SourceRightsDenied(PermissionError):
    """Raised only when a use is outside the private-research policy envelope.

    The legacy class name is retained for API compatibility. Licensing,
    redistribution ambiguity, provider preference, and missing upstream
    authorization are never reasons to raise this exception for private local
    acquisition or training.
    """


@dataclass(frozen=True)
class SourceRightsDecision:
    source_id: str
    provider: str
    dataset: str
    lane_disposition: str
    rights_decision: str
    authorized_acquisition_route: str
    production_acquisition_allowed: bool
    experimental_acquisition_allowed: bool
    raw_export_allowed: bool
    derived_export_allowed: bool
    local_model_training_allowed: bool
    substitute_source_ids: tuple[str, ...]
    revalidation_trigger: str

    def allows(self, action: SourceRightsAction) -> bool:
        return {
            SourceRightsAction.ACQUIRE_PRODUCTION: self.production_acquisition_allowed,
            SourceRightsAction.ACQUIRE_EXPERIMENTAL: self.experimental_acquisition_allowed,
            SourceRightsAction.EXPORT_RAW: self.raw_export_allowed,
            SourceRightsAction.EXPORT_DERIVED: self.derived_export_allowed,
            SourceRightsAction.TRAIN_LOCAL: self.local_model_training_allowed,
        }[action]


@dataclass(frozen=True)
class SourceRightsRegistry:
    schema_version: str
    registry_status: str
    decisions: dict[str, SourceRightsDecision]

    @classmethod
    def load(cls, path: Path, *, verify_inputs: bool = True) -> "SourceRightsRegistry":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "2.0.0":
            raise ValueError("SOURCE_RIGHTS_SCHEMA_UNSUPPORTED")
        if payload.get("registry_status") != "ACTIVE_PRIVATE_RESEARCH_POLICY":
            raise ValueError("SOURCE_RIGHTS_REGISTRY_NOT_VERIFIED")
        if payload.get("private_research_acquisition_default") != "ALLOW_PUBLIC_OR_OWNER_CREDENTIALED":
            raise ValueError("SOURCE_USE_PRIVATE_RESEARCH_DEFAULT_UNSAFE")
        if payload.get("rights_metadata_nonblocking") is not True:
            raise ValueError("SOURCE_USE_RIGHTS_METADATA_MUST_BE_NONBLOCKING")
        if payload.get("project_raw_export_default") != "DENY":
            raise ValueError("SOURCE_RIGHTS_RAW_EXPORT_DEFAULT_UNSAFE")
        entries = payload.get("sources")
        if not isinstance(entries, list) or not entries:
            raise ValueError("SOURCE_RIGHTS_SOURCES_MISSING")
        if payload.get("source_count") != len(entries):
            raise ValueError("SOURCE_RIGHTS_SOURCE_COUNT_MISMATCH")
        if verify_inputs:
            inputs = payload.get("inputs")
            if not isinstance(inputs, list) or not inputs:
                raise ValueError("SOURCE_RIGHTS_INPUT_IDENTITIES_MISSING")
            repository_root = path.resolve().parent.parent
            for identity in inputs:
                if not isinstance(identity, dict) or not isinstance(identity.get("path"), str):
                    raise ValueError("SOURCE_RIGHTS_INPUT_IDENTITY_INVALID")
                input_path = repository_root / identity["path"]
                if not input_path.is_file():
                    raise ValueError(f"SOURCE_RIGHTS_INPUT_MISSING:{identity['path']}")
                actual = hashlib.sha256(input_path.read_bytes()).hexdigest()
                if actual != identity.get("sha256"):
                    raise ValueError(f"SOURCE_RIGHTS_INPUT_IDENTITY_MISMATCH:{identity['path']}")
        decisions: dict[str, SourceRightsDecision] = {}
        required_booleans = (
            "production_acquisition_allowed",
            "experimental_acquisition_allowed",
            "raw_export_allowed",
            "derived_export_allowed",
            "local_model_training_allowed",
        )
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("SOURCE_RIGHTS_ENTRY_INVALID")
            source_id = entry.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                raise ValueError("SOURCE_RIGHTS_SOURCE_ID_MISSING")
            if source_id in decisions:
                raise ValueError(f"SOURCE_RIGHTS_DUPLICATE:{source_id}")
            if any(type(entry.get(name)) is not bool for name in required_booleans):
                raise ValueError(f"SOURCE_RIGHTS_BOOLEAN_INVALID:{source_id}")
            route = entry.get("authorized_acquisition_route")
            if not isinstance(route, str) or not route:
                raise ValueError(f"SOURCE_RIGHTS_ROUTE_MISSING:{source_id}")
            substitutes = entry.get("substitute_source_ids", [])
            if not isinstance(substitutes, list) or not all(isinstance(value, str) for value in substitutes):
                raise ValueError(f"SOURCE_RIGHTS_SUBSTITUTES_INVALID:{source_id}")
            if not (
                entry["production_acquisition_allowed"]
                and entry["experimental_acquisition_allowed"]
                and entry["local_model_training_allowed"]
            ):
                raise ValueError(f"SOURCE_USE_PRIVATE_RESEARCH_ACQUISITION_REQUIRED:{source_id}")
            if entry.get("lane_disposition") != "PRIVATE_RESEARCH_ALLOWED":
                raise ValueError(f"SOURCE_USE_STALE_RIGHTS_LANE:{source_id}")
            if entry["raw_export_allowed"] and not entry["production_acquisition_allowed"]:
                raise ValueError(f"SOURCE_RIGHTS_UNSAFE_RAW_EXPORT:{source_id}")
            if entry["raw_export_allowed"]:
                raise ValueError(f"SOURCE_RIGHTS_PROJECT_RAW_EXPORT_PROHIBITED:{source_id}")
            decisions[source_id] = SourceRightsDecision(
                source_id=source_id,
                provider=str(entry.get("provider", "")),
                dataset=str(entry.get("dataset", "")),
                lane_disposition=str(entry.get("lane_disposition", "")),
                rights_decision=str(entry.get("rights_decision", "")),
                authorized_acquisition_route=route,
                production_acquisition_allowed=entry["production_acquisition_allowed"],
                experimental_acquisition_allowed=entry["experimental_acquisition_allowed"],
                raw_export_allowed=entry["raw_export_allowed"],
                derived_export_allowed=entry["derived_export_allowed"],
                local_model_training_allowed=entry["local_model_training_allowed"],
                substitute_source_ids=tuple(substitutes),
                revalidation_trigger=str(entry.get("revalidation_trigger", "")),
            )
        return cls(
            schema_version=payload["schema_version"],
            registry_status=payload["registry_status"],
            decisions=decisions,
        )

    def require(
        self,
        source_id: str,
        action: SourceRightsAction | str,
        *,
        publicly_accessible: bool = False,
    ) -> SourceRightsDecision:
        try:
            normalized_action = action if isinstance(action, SourceRightsAction) else SourceRightsAction(action)
        except ValueError as exc:
            raise SourceRightsDenied(f"SOURCE_RIGHTS_ACTION_UNKNOWN:{action}") from exc
        decision = self.decisions.get(source_id)
        if decision is None:
            if publicly_accessible and normalized_action in {
                SourceRightsAction.ACQUIRE_PRODUCTION,
                SourceRightsAction.ACQUIRE_EXPERIMENTAL,
                SourceRightsAction.TRAIN_LOCAL,
            }:
                return SourceRightsDecision(
                    source_id=source_id,
                    provider="UNREGISTERED_PUBLIC_SOURCE",
                    dataset="UNREGISTERED_PUBLIC_FACTUAL_DATA",
                    lane_disposition="PRIVATE_RESEARCH_ALLOWED",
                    rights_decision="METADATA_ONLY_NONBLOCKING",
                    authorized_acquisition_route="CALLER_DECLARED_PUBLICLY_ACCESSIBLE_ROUTE",
                    production_acquisition_allowed=True,
                    experimental_acquisition_allowed=True,
                    raw_export_allowed=False,
                    derived_export_allowed=False,
                    local_model_training_allowed=True,
                    substitute_source_ids=(),
                    revalidation_trigger="PUBLIC_DISTRIBUTION_OR_COMMERCIALIZATION_PROPOSED",
                )
            raise SourceRightsDenied(f"SOURCE_USE_PUBLIC_ACCESS_UNCONFIRMED:{source_id}")
        if not decision.allows(normalized_action):
            substitutes = ";".join(decision.substitute_source_ids) or "NONE"
            raise SourceRightsDenied(
                f"SOURCE_USE_DENIED:{source_id}:{normalized_action.value}:"
                f"{decision.lane_disposition}:SUBSTITUTES={substitutes}"
            )
        return decision

@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    dataset: str
    row_number: int
    payload: dict[str, Any]

@dataclass(frozen=True)
class RawSnapshot:
    snapshot_id: str
    source_id: str
    dataset: str
    retrieved_at: datetime
    raw_sha256: str
    relative_path: str
    row_count: int
    schema_fields: tuple[str,...]
    source_uri: str
    publication_time: datetime|None = None
    metadata: dict[str,Any] = field(default_factory=dict)

@dataclass(frozen=True)
class SnapshotManifest:
    version: str
    snapshots: tuple[RawSnapshot,...]

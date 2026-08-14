from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .controller_state import ControllerState


def _canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _content_addressed_write(
    root: Path,
    category: str,
    payload: dict[str, Any],
    *,
    current_name: str,
) -> tuple[Path, str]:
    data = _canonical_json_bytes(payload)
    digest = hashlib.sha256(data).hexdigest()
    immutable = root / category / "sha256" / digest / "report.json"
    immutable.parent.mkdir(parents=True, exist_ok=True)
    if immutable.exists():
        if immutable.read_bytes() != data:
            raise RuntimeError("DOWNSTREAM_REVIEW_EVIDENCE_COLLISION")
    else:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{immutable.name}.", suffix=".tmp", dir=immutable.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(immutable)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    current = root / "current" / current_name
    current.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{current.name}.", suffix=".tmp", dir=current.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(current)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return immutable, digest


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


@dataclass(frozen=True)
class DownstreamReviewConfig:
    registry_path: Path
    evidence_root: Path
    releases_root: Path | None = None
    max_per_cycle: int = 16

    def validate(self) -> None:
        if not self.registry_path.is_absolute() or not self.registry_path.is_file():
            raise ValueError("DOWNSTREAM_REVIEW_REGISTRY_MISSING")
        if not self.evidence_root.is_absolute():
            raise ValueError("DOWNSTREAM_REVIEW_EVIDENCE_ROOT_NOT_ABSOLUTE")
        if self.releases_root is not None and not self.releases_root.is_absolute():
            raise ValueError("DOWNSTREAM_REVIEW_RELEASES_ROOT_NOT_ABSOLUTE")
        if self.max_per_cycle <= 0:
            raise ValueError("DOWNSTREAM_REVIEW_BOUND_INVALID")


class DownstreamReviewConsumer:
    """Route validated candidates or apply exact final-authority adoption decisions."""

    def __init__(self, state: ControllerState, config: DownstreamReviewConfig) -> None:
        config.validate()
        self.state = state
        self.config = config

    def _registry(
        self,
    ) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
        payload = json.loads(self.config.registry_path.read_text(encoding="utf-8"))
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != 1
            or payload.get("artifact_type") != "ASSISTIVE_DOWNSTREAM_ADOPTION_REGISTRY"
            or payload.get("authority") != "CODEX_FINAL_INTEGRATION_ONLY"
            or payload.get("default_disposition") != "PENDING_NO_REGISTERED_CONSUMER"
            or not isinstance(payload.get("entries"), list)
        ):
            raise ValueError("DOWNSTREAM_REVIEW_REGISTRY_INVALID")
        entries: dict[str, dict[str, Any]] = {}
        for entry in payload["entries"]:
            if not isinstance(entry, dict):
                raise ValueError("DOWNSTREAM_REVIEW_ENTRY_INVALID")
            digest = entry.get("result_artifact_sha256")
            if (
                not _valid_sha256(digest)
                or digest in entries
                or entry.get("disposition") not in {"ACCEPTED", "MODIFIED"}
                or not _valid_sha256(entry.get("consumed_artifact_identity"))
                or not isinstance(entry.get("work_unit_id"), str)
                or not _valid_sha256(entry.get("attempt_id"))
                or not isinstance(entry.get("provider"), str)
                or not isinstance(entry.get("downstream_consumer"), str)
                or not isinstance(entry.get("merged_commit"), str)
                or len(entry.get("merged_commit", "")) != 40
                or any(
                    character not in "0123456789abcdef"
                    for character in entry.get("merged_commit", "")
                )
                or entry.get("changed_project_artifact") is not True
                or entry.get("duplicated_by_codex") is not False
                or float(entry.get("net_time_saved_seconds", -1.0)) < 0.0
                or float(entry.get("review_seconds", -1.0)) < 0.0
                or not isinstance(entry.get("reason"), str)
                or not entry["reason"]
            ):
                raise ValueError("DOWNSTREAM_REVIEW_ENTRY_INVALID")
            entries[str(digest)] = entry
        candidate_contracts: dict[tuple[str, str], dict[str, Any]] = {}
        contracts = payload.get("candidate_contracts", [])
        if not isinstance(contracts, list):
            raise ValueError("DOWNSTREAM_REVIEW_CANDIDATE_CONTRACTS_INVALID")
        for contract in contracts:
            if not isinstance(contract, dict):
                raise ValueError("DOWNSTREAM_REVIEW_CANDIDATE_CONTRACT_INVALID")
            provider = contract.get("provider")
            task_category = contract.get("task_category")
            identity = (str(provider), str(task_category))
            if (
                not isinstance(provider, str)
                or not provider
                or not isinstance(task_category, str)
                or not task_category
                or identity in candidate_contracts
                or contract.get("contract_version") != "candidate-review-routing-v1"
                or not isinstance(contract.get("downstream_consumer"), str)
                or not contract["downstream_consumer"]
                or contract.get("authority") != "CANDIDATE_REVIEW_QUEUE_ONLY"
            ):
                raise ValueError("DOWNSTREAM_REVIEW_CANDIDATE_CONTRACT_INVALID")
            candidate_contracts[identity] = contract
        return entries, candidate_contracts

    @staticmethod
    def _validate_candidate_result(
        candidate: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        response = payload.get("result")
        if (
            payload.get("schema_version") != 1
            or payload.get("artifact_type") != "GOVERNED_PROVIDER_CANDIDATE_RESULT"
            or payload.get("authority") != "CANDIDATE_ONLY"
            or payload.get("provider") != candidate["provider"]
            or payload.get("work_unit_id") != candidate["work_unit_id"]
            or payload.get("attempt_id") != candidate["attempt_id"]
            or payload.get("disposition") not in {"REVIEW_ONLY", "ACCEPTED", "MODIFIED"}
            or payload.get("validation_errors") != []
            or not isinstance(response, dict)
            or response.get("authority") != "CANDIDATE_ONLY"
            or response.get("canonical_writes") != 0
            or response.get("protected_decisions") != 0
        ):
            raise RuntimeError("DOWNSTREAM_CANDIDATE_RESULT_AUTHORITY_INVALID")

    def process(self, *, now: datetime | None = None) -> dict[str, Any]:
        moment = now or datetime.now(timezone.utc)
        registry, candidate_contracts = self._registry()
        provider_summary = self.state.provider_run_summary()
        total_pending = sum(
            int(summary.get("pending_downstream_review", 0))
            for summary in provider_summary.values()
        )
        pending = self.state.pending_downstream_reviews(
            limit=self.config.max_per_cycle,
            result_artifact_sha256s=set(registry),
        )
        applied: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        evidence_root = self.config.evidence_root.resolve(strict=False)
        for candidate in pending:
            artifact_path = Path(str(candidate["result_artifact_path"])).resolve(
                strict=True
            )
            if evidence_root not in artifact_path.parents:
                raise RuntimeError("DOWNSTREAM_REVIEW_RESULT_OUTSIDE_EVIDENCE_ROOT")
            artifact_sha256 = _sha256_file(artifact_path)
            if artifact_sha256 != candidate["result_artifact_sha256"]:
                raise RuntimeError("DOWNSTREAM_REVIEW_RESULT_HASH_MISMATCH")
            entry = registry.get(artifact_sha256)
            if entry is None:
                raise RuntimeError("DOWNSTREAM_REVIEW_REGISTERED_RESULT_NOT_RESOLVED")
            if any(
                str(candidate[key]) != str(entry[key])
                for key in ("attempt_id", "work_unit_id", "provider")
            ):
                raise RuntimeError("DOWNSTREAM_REVIEW_REGISTRY_IDENTITY_MISMATCH")
            if self.config.releases_root is not None:
                release_manifest_path = (
                    self.config.releases_root
                    / str(entry["merged_commit"])
                    / "RELEASE_MANIFEST.json"
                )
                release_manifest = json.loads(
                    release_manifest_path.read_text(encoding="utf-8")
                )
                if (
                    release_manifest.get("build_commit") != entry["merged_commit"]
                    or release_manifest.get("source_tree_sha256")
                    != entry["consumed_artifact_identity"]
                ):
                    raise RuntimeError(
                        "DOWNSTREAM_REVIEW_CONSUMED_RELEASE_IDENTITY_MISMATCH"
                    )
            decision = {
                "schema_version": 1,
                "artifact_type": "ASSISTIVE_DOWNSTREAM_REVIEW_DECISION",
                "recorded_at": moment.isoformat().replace("+00:00", "Z"),
                "attempt_id": str(candidate["attempt_id"]),
                "work_unit_id": str(candidate["work_unit_id"]),
                "provider": str(candidate["provider"]),
                "result_artifact_sha256": artifact_sha256,
                "disposition": str(entry["disposition"]),
                "downstream_consumer": str(entry["downstream_consumer"]),
                "consumed_artifact_identity": str(entry["consumed_artifact_identity"]),
                "merged_commit": str(entry.get("merged_commit", "")),
                "changed_project_artifact": True,
                "net_time_saved_seconds": float(entry["net_time_saved_seconds"]),
                "duplicated_by_codex": False,
                "review_seconds": float(entry["review_seconds"]),
                "reason": str(entry["reason"]),
                "accepted_useful_offload_credit": (
                    float(entry["net_time_saved_seconds"]) > 0.0
                ),
            }
            decision_path, decision_sha256 = _content_addressed_write(
                self.config.evidence_root,
                "downstream-review-decisions",
                decision,
                current_name=f"downstream-review-{candidate['attempt_id']}.json",
            )
            disposition_sha256 = self.state.record_downstream_review_disposition(
                attempt_id=str(candidate["attempt_id"]),
                disposition=str(entry["disposition"]),
                downstream_consumer=str(entry["downstream_consumer"]),
                reason=str(entry["reason"]),
                consumed_artifact_identity=str(entry["consumed_artifact_identity"]),
                changed_project_artifact=True,
                net_time_saved_seconds=float(entry["net_time_saved_seconds"]),
                duplicated_by_codex=False,
                review_seconds=float(entry["review_seconds"]),
                now=moment,
            )
            applied.append(
                {
                    "attempt_id": str(candidate["attempt_id"]),
                    "work_unit_id": str(candidate["work_unit_id"]),
                    "provider": str(candidate["provider"]),
                    "disposition": str(entry["disposition"]),
                    "decision_path": str(decision_path),
                    "decision_sha256": decision_sha256,
                    "disposition_sha256": disposition_sha256,
                    "accepted_useful_offload_credit": decision[
                        "accepted_useful_offload_credit"
                    ],
                }
            )
        remaining_capacity = max(0, self.config.max_per_cycle - len(applied))
        if remaining_capacity:
            for candidate in self.state.pending_downstream_reviews(
                limit=remaining_capacity
            ):
                artifact_sha256 = str(candidate["result_artifact_sha256"])
                if artifact_sha256 in registry:
                    continue
                contract = candidate_contracts.get(
                    (str(candidate["provider"]), str(candidate.get("task_category")))
                )
                if contract is None:
                    continue
                try:
                    artifact_path = Path(
                        str(candidate["result_artifact_path"])
                    ).resolve(strict=True)
                    if evidence_root not in artifact_path.parents:
                        raise RuntimeError(
                            "DOWNSTREAM_REVIEW_RESULT_OUTSIDE_EVIDENCE_ROOT"
                        )
                    if _sha256_file(artifact_path) != artifact_sha256:
                        raise RuntimeError("DOWNSTREAM_REVIEW_RESULT_HASH_MISMATCH")
                    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
                    if not isinstance(payload, dict):
                        raise RuntimeError("DOWNSTREAM_CANDIDATE_RESULT_INVALID")
                    self._validate_candidate_result(candidate, payload)
                    decision = {
                        "schema_version": 1,
                        "artifact_type": "ASSISTIVE_CANDIDATE_REVIEW_ROUTING",
                        "recorded_at": str(candidate["review_recorded_at"]),
                        "attempt_id": str(candidate["attempt_id"]),
                        "work_unit_id": str(candidate["work_unit_id"]),
                        "provider": str(candidate["provider"]),
                        "task_category": str(candidate["task_category"]),
                        "pre_routing_decision_sha256": str(
                            candidate["pre_routing_decision_sha256"]
                        ),
                        "packet_identity": str(candidate["packet_identity"]),
                        "source_review_sha256": str(candidate["source_review_sha256"]),
                        "result_artifact_sha256": artifact_sha256,
                        "contract_version": str(contract["contract_version"]),
                        "downstream_consumer": str(contract["downstream_consumer"]),
                        "disposition": "REVIEW_ONLY_IN_CANDIDATE_QUEUE",
                        "authority": "CANDIDATE_REVIEW_QUEUE_ONLY_NO_FACTUAL_CANONICAL_OR_PROTECTED_ACCEPTANCE",
                        "changed_project_artifact": False,
                        "net_time_saved_seconds": 0.0,
                        "duplicated_by_codex": False,
                        "accepted_useful_offload_credit": False,
                    }
                    decision_path, decision_sha256 = _content_addressed_write(
                        self.config.evidence_root,
                        "candidate-review-routing",
                        decision,
                        current_name=f"candidate-review-{candidate['attempt_id']}.json",
                    )
                    disposition_sha256 = self.state.record_downstream_review_disposition(
                        attempt_id=str(candidate["attempt_id"]),
                        disposition="ACCEPTED",
                        downstream_consumer=str(contract["downstream_consumer"]),
                        reason=(
                            "VALIDATED_PROVIDER_RESULT_ACCEPTED_ONLY_INTO_NONAUTHORITATIVE_"
                            "CANDIDATE_REVIEW_QUEUE; ZERO_FACTUAL_ACCEPTANCE_AND_ZERO_SAVINGS_CREDIT"
                        ),
                        consumed_artifact_identity=decision_sha256,
                        changed_project_artifact=False,
                        net_time_saved_seconds=0.0,
                        duplicated_by_codex=False,
                        review_seconds=0.0,
                        now=moment,
                    )
                    applied.append(
                        {
                            "attempt_id": str(candidate["attempt_id"]),
                            "work_unit_id": str(candidate["work_unit_id"]),
                            "provider": str(candidate["provider"]),
                            "disposition": "REVIEW_ONLY",
                            "downstream_disposition": "ACCEPTED",
                            "decision_path": str(decision_path),
                            "decision_sha256": decision_sha256,
                            "disposition_sha256": disposition_sha256,
                            "accepted_useful_offload_credit": False,
                            "candidate_review_queue_only": True,
                        }
                    )
                except Exception as exc:
                    failures.append(
                        {
                            "attempt_id": str(candidate["attempt_id"]),
                            "work_unit_id": str(candidate["work_unit_id"]),
                            "provider": str(candidate["provider"]),
                            "finding": type(exc).__name__ + ":" + str(exc)[:240],
                        }
                    )
        deferred = max(0, total_pending - len(applied))
        deferred_sample = [
            {
                "attempt_id": str(candidate["attempt_id"]),
                "work_unit_id": str(candidate["work_unit_id"]),
                "provider": str(candidate["provider"]),
                "reason": "PENDING_NO_REGISTERED_DOWNSTREAM_CONSUMER",
            }
            for candidate in self.state.pending_downstream_reviews(
                limit=min(16, self.config.max_per_cycle)
            )
        ]
        return {
            "result": "PASS",
            "processed": len(applied),
            "deferred": deferred,
            "applied": applied,
            "failures": failures,
            "deferred_candidates": deferred_sample,
        }

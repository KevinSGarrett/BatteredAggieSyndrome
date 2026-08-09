from __future__ import annotations

"""Local-first queue prioritization and bounded resource admission."""

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


PRIORITY_RANK = {"MUST": 0, "SHOULD": 1, "RESEARCH": 2, "COULD": 3, "DEFERRED": 4}


@dataclass(frozen=True)
class ResourceRequest:
    cpu_threads: int = 1
    ram_mb: int = 1024
    gpu_slots: int = 0
    vram_mb: int = 0
    disk_mb: int = 1024
    paid_compute: bool = False

    def validate(self) -> None:
        for name in ("cpu_threads", "ram_mb", "gpu_slots", "vram_mb", "disk_mb"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")


@dataclass(frozen=True)
class ResourcePool:
    cpu_threads: int
    ram_mb: int
    gpu_slots: int = 0
    vram_mb: int = 0
    disk_mb: int = 0
    paid_compute_approved: bool = False


@dataclass(frozen=True)
class QueueCandidate:
    experiment_id: str
    priority: str
    dependency_ready: bool
    owner_wave_active: bool
    protected_rule_seal_valid: bool
    shared_contract_conflict: bool
    request: ResourceRequest
    queue_index: int
    tags: Sequence[str] = field(default_factory=tuple)


def can_admit(candidate: QueueCandidate, pool: ResourcePool) -> tuple[bool, tuple[str, ...]]:
    candidate.request.validate()
    reasons: list[str] = []
    if not candidate.dependency_ready:
        reasons.append("DEPENDENCY_BLOCKED")
    if not candidate.owner_wave_active:
        reasons.append("OWNER_WAVE_INACTIVE")
    if not candidate.protected_rule_seal_valid:
        reasons.append("JUDGING_RULE_SEAL_INVALID")
    if candidate.shared_contract_conflict:
        reasons.append("SHARED_CONTRACT_CONFLICT")
    r = candidate.request
    if r.cpu_threads > pool.cpu_threads:
        reasons.append("CPU_BUDGET_EXCEEDED")
    if r.ram_mb > pool.ram_mb:
        reasons.append("RAM_BUDGET_EXCEEDED")
    if r.gpu_slots > pool.gpu_slots:
        reasons.append("GPU_SLOT_BUDGET_EXCEEDED")
    if r.vram_mb > pool.vram_mb:
        reasons.append("VRAM_BUDGET_EXCEEDED")
    if r.disk_mb > pool.disk_mb:
        reasons.append("DISK_BUDGET_EXCEEDED")
    if r.paid_compute and not pool.paid_compute_approved:
        reasons.append("PAID_COMPUTE_NOT_APPROVED")
    return (not reasons, tuple(reasons))


def rank_queue(candidates: Iterable[QueueCandidate]) -> list[QueueCandidate]:
    def key(c: QueueCandidate):
        return (
            0 if c.dependency_ready else 1,
            0 if c.owner_wave_active else 1,
            PRIORITY_RANK.get(c.priority, 99),
            c.queue_index,
            c.experiment_id,
        )
    return sorted(candidates, key=key)


def select_admissible(candidates: Iterable[QueueCandidate], pool: ResourcePool, limit: int) -> list[QueueCandidate]:
    if limit < 1:
        raise ValueError("limit must be positive")
    selected: list[QueueCandidate] = []
    remaining = ResourcePool(
        cpu_threads=pool.cpu_threads, ram_mb=pool.ram_mb,
        gpu_slots=pool.gpu_slots, vram_mb=pool.vram_mb,
        disk_mb=pool.disk_mb, paid_compute_approved=pool.paid_compute_approved,
    )
    for candidate in rank_queue(candidates):
        ok, _ = can_admit(candidate, remaining)
        if not ok:
            continue
        selected.append(candidate)
        r = candidate.request
        remaining = ResourcePool(
            cpu_threads=remaining.cpu_threads-r.cpu_threads,
            ram_mb=remaining.ram_mb-r.ram_mb,
            gpu_slots=remaining.gpu_slots-r.gpu_slots,
            vram_mb=remaining.vram_mb-r.vram_mb,
            disk_mb=remaining.disk_mb-r.disk_mb,
            paid_compute_approved=remaining.paid_compute_approved,
        )
        if len(selected) >= limit:
            break
    return selected

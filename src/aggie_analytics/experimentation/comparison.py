from __future__ import annotations

"""Development-only result compatibility and Pareto comparison helpers."""

from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence


SEMANTIC_KEYS = (
    "target", "split_id", "data_snapshot_id", "feature_version", "metric_registry_version",
    "lane", "bas_anchor_version", "tamu_baseline_version",
)


@dataclass(frozen=True)
class MetricValue:
    name: str
    value: float
    direction: str  # min|max

    def validate(self) -> None:
        if self.direction not in {"min", "max"}:
            raise ValueError("direction must be min/max")
        if not isfinite(self.value):
            raise ValueError("metric value must be finite")


def assert_semantically_compatible(left: Mapping[str, object], right: Mapping[str, object]) -> None:
    mismatched = [k for k in SEMANTIC_KEYS if left.get(k) != right.get(k)]
    if mismatched:
        raise ValueError(f"incompatible result packets: {mismatched}")
    for packet in (left, right):
        split = str(packet.get("split_id", ""))
        if split not in {"SPLIT-DEV-HIST", "SPLIT-DEV-SEL"}:
            raise ValueError("research-plane direct comparison must be development-only")


def metric_delta(candidate: MetricValue, baseline: MetricValue) -> float:
    candidate.validate(); baseline.validate()
    if candidate.name != baseline.name or candidate.direction != baseline.direction:
        raise ValueError("metrics must share name and direction")
    if candidate.direction == "min":
        return baseline.value - candidate.value  # positive means candidate improved
    return candidate.value - baseline.value


def pareto_dominated(candidate: Mapping[str, MetricValue], other: Mapping[str, MetricValue]) -> bool:
    common = sorted(set(candidate).intersection(other))
    if not common:
        raise ValueError("no common metrics")
    deltas = [metric_delta(candidate[name], other[name]) for name in common]
    # candidate is dominated when other is >= on all metrics and > on at least one.
    return all(d <= 0 for d in deltas) and any(d < 0 for d in deltas)


def ordered_development_ranking(
    packets: Sequence[Mapping[str, object]],
    *,
    primary_metric: str,
    direction: str,
) -> list[Mapping[str, object]]:
    if direction not in {"min", "max"}:
        raise ValueError("direction must be min/max")
    for packet in packets:
        split = str(packet.get("split_id", ""))
        if split not in {"SPLIT-DEV-HIST", "SPLIT-DEV-SEL"}:
            raise ValueError("protected/forward packet cannot enter research ranking")
        if primary_metric not in packet.get("metrics", {}):
            raise ValueError(f"packet missing primary metric {primary_metric}")
    reverse = direction == "max"
    return sorted(
        packets,
        key=lambda p: (float(p["metrics"][primary_metric]), str(p.get("experiment_id", ""))),
        reverse=reverse,
    )

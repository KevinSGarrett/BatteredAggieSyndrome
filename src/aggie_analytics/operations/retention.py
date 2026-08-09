from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class RetentionRule:
    retention_class: str
    minimum_days: int | None
    automatic_delete_allowed: bool
    rationale: str

DEFAULT_RULES = {
    "GOVERNANCE": RetentionRule("GOVERNANCE", None, False, "Canonical governance/history is retained."),
    "PUBLISHED_FORECAST": RetentionRule("PUBLISHED_FORECAST", None, False, "Published forecasts are immutable historical evidence."),
    "CHAMPION_HISTORY": RetentionRule("CHAMPION_HISTORY", None, False, "Promotion/rollback history is audit evidence."),
    "EXPERIMENT_EVIDENCE": RetentionRule("EXPERIMENT_EVIDENCE", 365, False, "Deletion requires explicit reviewed policy."),
    "TRANSIENT_CACHE": RetentionRule("TRANSIENT_CACHE", 14, True, "Regenerable cache may be pruned after minimum age."),
}

def retention_rule(name: str) -> RetentionRule:
    try: return DEFAULT_RULES[name]
    except KeyError as exc: raise ValueError(f"unknown retention class: {name}") from exc

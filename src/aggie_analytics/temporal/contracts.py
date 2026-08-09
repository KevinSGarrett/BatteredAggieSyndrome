from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


def parse_time(value: str | datetime | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = value.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("PIT timestamps must be timezone-aware")
    return dt


@dataclass(frozen=True)
class ForecastCutoff:
    cutoff_id: str
    purpose: str
    prediction_timestamp: datetime
    target_event_time: datetime
    forecast_lane: str
    temporal_policy_version: str
    data_snapshot_id: str
    target_game_id: str | None = None

    def __post_init__(self) -> None:
        if self.prediction_timestamp.tzinfo is None or self.target_event_time.tzinfo is None:
            raise ValueError("cutoff timestamps must be timezone-aware")


@dataclass(frozen=True)
class TemporalObservation:
    observation_id: str
    source_observation_id: str
    domain: str
    retrieved_at: datetime
    temporal_policy_version: str
    first_known_at: datetime | None = None
    published_at: datetime | None = None
    observed_at: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    retrospective_flag: bool = False
    corroborated_for_historical_use: bool = False
    supersedes_observation_id: str | None = None
    attributes: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "TemporalObservation":
        known = {k: data.get(k) for k in [
            "observation_id", "source_observation_id", "domain", "temporal_policy_version",
            "retrospective_flag", "corroborated_for_historical_use", "supersedes_observation_id"
        ]}
        for key in ["retrieved_at","first_known_at","published_at","observed_at","valid_from","valid_to"]:
            known[key] = parse_time(data.get(key))
        structural=set(known) | {"retrieved_at","first_known_at","published_at","observed_at","valid_from","valid_to"}
        known["attributes"]={k:v for k,v in data.items() if k not in structural}
        return cls(**known)

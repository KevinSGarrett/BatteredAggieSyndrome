from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ExecutionLane(StrEnum):
    OFFLINE_BATCH = "OFFLINE_BATCH"
    FORECAST_REFRESH = "FORECAST_REFRESH"
    SERVING_READ = "SERVING_READ"
    RESEARCH = "RESEARCH"
    FUTURE_LIVE = "FUTURE_LIVE"


class MarketLane(StrEnum):
    PURE_FOOTBALL = "PURE_FOOTBALL"
    MARKET_AUGMENTED = "MARKET_AUGMENTED"


@dataclass(frozen=True)
class AsOfContext:
    """Minimal temporal contract shared by future PIT-aware interfaces.

    W03 deliberately does not define the full W08 PIT schema. This contract only
    enforces that the data cutoff cannot occur after the prediction timestamp.
    """

    prediction_timestamp_utc: datetime
    data_cutoff_utc: datetime

    def __post_init__(self) -> None:
        if self.prediction_timestamp_utc.tzinfo is None or self.data_cutoff_utc.tzinfo is None:
            raise ValueError("AsOfContext timestamps must be timezone-aware")
        if self.data_cutoff_utc > self.prediction_timestamp_utc:
            raise ValueError("data_cutoff_utc cannot be after prediction_timestamp_utc")

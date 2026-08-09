from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Sequence

SNAPSHOT_SCHEMA_V1 = "aggie.forecast.snapshot.v1"
SNAPSHOT_SCHEMA_V2 = "aggie.forecast.snapshot.v2"
MARKET_LANES = frozenset({"PURE_FOOTBALL", "MARKET_AUGMENTED"})


def _aware_datetime(value: str | datetime, *, field_name: str) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed


def _tuple_of_dicts(value: Any) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("expected a sequence of objects")
    out: list[Mapping[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("expected a sequence of objects")
        out.append(dict(item))
    return tuple(out)


@dataclass(frozen=True)
class PublishedForecastSnapshot:
    snapshot_id: str
    game_id: str
    forecast_cutoff: datetime
    published_at: datetime
    model_artifact_sha256: str
    feature_snapshot_id: str
    public_summary: Mapping[str, float]
    lineage_refs: tuple[str, ...]
    schema_version: str = SNAPSHOT_SCHEMA_V1
    market_lane: str = "PURE_FOOTBALL"
    teams: Mapping[str, str] = field(default_factory=dict)
    uncertainty: tuple[Mapping[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    availability: tuple[Mapping[str, Any], ...] = ()
    matchup_explanation: tuple[Mapping[str, Any], ...] = ()
    historical_analogs: tuple[Mapping[str, Any], ...] = ()
    source_metadata: tuple[Mapping[str, Any], ...] = ()
    model_metadata: Mapping[str, Any] = field(default_factory=dict)
    data_snapshot_refs: tuple[str, ...] = ()
    comparison_context: Mapping[str, Any] = field(default_factory=dict)
    public_metadata: Mapping[str, Any] = field(default_factory=dict)
    artifact_ref: str | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, artifact_ref: str | None = None) -> "PublishedForecastSnapshot":
        required = (
            "snapshot_id", "game_id", "forecast_cutoff", "published_at",
            "model_artifact_sha256", "feature_snapshot_id", "public_summary", "lineage_refs",
        )
        missing = [name for name in required if name not in payload]
        if missing:
            raise ValueError(f"published forecast missing required fields: {missing}")
        summary = payload["public_summary"]
        if not isinstance(summary, Mapping):
            raise ValueError("public_summary must be an object")
        numeric_summary: dict[str, float] = {}
        for key, value in summary.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"public_summary[{key!r}] must be numeric")
            numeric_summary[str(key)] = float(value)
        lane = str(payload.get("market_lane", "PURE_FOOTBALL"))
        if lane not in MARKET_LANES:
            raise ValueError(f"unsupported market lane: {lane}")
        lineage = tuple(str(x) for x in payload["lineage_refs"])
        if not lineage:
            raise ValueError("lineage_refs must not be empty")
        obj = cls(
            snapshot_id=str(payload["snapshot_id"]),
            game_id=str(payload["game_id"]),
            forecast_cutoff=_aware_datetime(payload["forecast_cutoff"], field_name="forecast_cutoff"),
            published_at=_aware_datetime(payload["published_at"], field_name="published_at"),
            model_artifact_sha256=str(payload["model_artifact_sha256"]),
            feature_snapshot_id=str(payload["feature_snapshot_id"]),
            public_summary=numeric_summary,
            lineage_refs=lineage,
            schema_version=str(payload.get("schema_version", SNAPSHOT_SCHEMA_V1)),
            market_lane=lane,
            teams=dict(payload.get("teams") or {}),
            uncertainty=_tuple_of_dicts(payload.get("uncertainty")),
            warnings=tuple(str(x) for x in (payload.get("warnings") or ())),
            availability=_tuple_of_dicts(payload.get("availability")),
            matchup_explanation=_tuple_of_dicts(payload.get("matchup_explanation")),
            historical_analogs=_tuple_of_dicts(payload.get("historical_analogs")),
            source_metadata=_tuple_of_dicts(payload.get("source_metadata")),
            model_metadata=dict(payload.get("model_metadata") or {}),
            data_snapshot_refs=tuple(str(x) for x in (payload.get("data_snapshot_refs") or ())),
            comparison_context=dict(payload.get("comparison_context") or {}),
            public_metadata=dict(payload.get("public_metadata") or {}),
            artifact_ref=artifact_ref,
        )
        obj.validate()
        return obj

    def validate(self) -> None:
        if not all((self.snapshot_id, self.game_id, self.model_artifact_sha256, self.feature_snapshot_id)):
            raise ValueError("published snapshot identity is incomplete")
        if self.forecast_cutoff.tzinfo is None or self.published_at.tzinfo is None:
            raise ValueError("published snapshot timestamps must be timezone-aware")
        if self.published_at < self.forecast_cutoff:
            raise ValueError("published_at cannot precede forecast_cutoff")
        if self.market_lane not in MARKET_LANES:
            raise ValueError("invalid market lane")
        for key, value in self.public_summary.items():
            if key.endswith("probability") or key.startswith("bas_"):
                if not 0.0 <= float(value) <= 1.0:
                    raise ValueError(f"probability-like summary value out of range: {key}")

    @property
    def team_name(self) -> str:
        return str(self.teams.get("team_name") or self.teams.get("team") or "Texas A&M")

    @property
    def opponent_name(self) -> str:
        return str(self.teams.get("opponent_name") or self.teams.get("opponent") or "Opponent")
